"""
app/agents/crew.py
───────────────────
CrewAI multi-agent crew builder and execution orchestrator.

Orchestrates the 6 agents using Process.sequential, passing rich context
from prior tasks to subsequent tasks.
Extracts both raw agent logs and typed Pydantic models (StrategyReport, VerificationResult).
Includes step and task callbacks for real-time frontend monitoring.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Callable

from crewai import Crew, Process

from app.agents.agents import create_retail_agents
from app.agents.llm import get_llm
from app.agents.tasks import StrategyReport, VerificationResult, create_retail_tasks
from app.agents.tools import build_tools
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


def run_crew(
    dataset_id: uuid.UUID,
    business_profile: dict[str, Any] | None = None,
    user_question: str | None = None,
    feedback: str | None = None,
    step_callback: Callable[[Any], None] | None = None,
    task_callback: Callable[[Any], None] | None = None,
) -> dict[str, Any]:
    """
    Constructs and executes the 6-agent CrewAI intelligence pipeline.

    Workflow:
      Data Analyst → Marketing → Finance → Operations → Strategy → Verification

    Args:
        dataset_id: Target dataset UUID.
        business_profile: Optional business profile dictionary.
        user_question: Optional targeted question from user.
        feedback: Optional previous feedback for iterative refinement.
        step_callback: Optional callback invoked on each agent step (for SSE streaming).
        task_callback: Optional callback invoked when each task completes.

    Returns:
        Structured dictionary containing:
          - strategy_report: Parsed StrategyReport Pydantic object / dict
          - verification_result: Parsed VerificationResult Pydantic object / dict
          - agent_outputs: Dictionary mapping agent role to its raw output string
          - execution_time_seconds: Total pipeline duration
          - status: 'completed' | 'verification_failed' | 'failed'
    """
    start_time = time.time()
    logger.info("Initializing CrewAI execution for dataset: %s", dataset_id)

    # 1. Build server-side bound tools (dataset_id is locked in closure)
    tools = build_tools(dataset_id=dataset_id, db_session_factory=SessionLocal)

    # 2. Get LLM configured with low temperature (0.2)
    llm = get_llm()

    # 3. Create the 6 specialized agents
    agents_dict = create_retail_agents(tools=tools, business_profile=business_profile, llm=llm)

    # 4. Create tasks with explicit sequential context pipelines
    tasks_list = create_retail_tasks(
        agents=agents_dict,
        user_question=user_question,
        feedback=feedback,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Process Execution Strategy: Sequential vs. Hierarchical
    # ─────────────────────────────────────────────────────────────────────────
    # We use Process.sequential because business intelligence reports require
    # a strict analytical precedence:
    # 1. Baseline analysis must complete first (Data Analyst)
    # 2. Domain agents analyze customer, finance, and operational facets (Marketing, Finance, Operations)
    # 3. Cross-functional synthesis occurs (Strategy)
    # 4. Independent numerical audit concludes the pipeline (Verification)
    #
    # ── Hierarchical Execution Alternative (Commented Reference) ───────────────
    # If the user desires dynamic delegation where an autonomous manager plans
    # and routes subtasks among agents, CrewAI's Process.hierarchical can be used:
    #
    # hierarchical_crew = Crew(
    #     agents=list(agents_dict.values()),
    #     tasks=tasks_list,
    #     process=Process.hierarchical,
    #     manager_llm=llm,
    #     verbose=True,
    #     step_callback=step_callback,
    #     task_callback=task_callback,
    # )
    # ─────────────────────────────────────────────────────────────────────────

    crew = Crew(
        agents=list(agents_dict.values()),
        tasks=tasks_list,
        process=Process.sequential,
        verbose=True,
        step_callback=step_callback,
        task_callback=task_callback,
    )

    inputs = {
        "dataset_period": "May 1, 2026 – October 31, 2026",
        "company_name": business_profile.get("company_name", "Retail Enterprise") if business_profile else "Retail Enterprise",
        "industry": "Retail - Sales & Inventory Intelligence",
    }
    if user_question:
        inputs["user_question"] = user_question
    if feedback:
        inputs["feedback"] = feedback

    logger.info("Kicking off sequential CrewAI workflow...")
    crew_output = crew.kickoff(inputs=inputs)
    duration = round(time.time() - start_time, 2)
    logger.info("Crew execution completed in %s seconds", duration)

    # 5. Extract Task Outputs
    agent_outputs: dict[str, str] = {}
    task_keys = ["data_analyst", "marketing", "finance", "operations", "strategy", "verification"]
    for idx, task_obj in enumerate(tasks_list):
        key = task_keys[idx] if idx < len(task_keys) else f"agent_{idx}"
        raw_val = getattr(task_obj.output, "raw", str(task_obj.output)) if hasattr(task_obj, "output") and task_obj.output else ""
        agent_outputs[key] = raw_val

    # 6. Extract Typed Outputs for Strategy (Task 5) and Verification (Task 6)
    strategy_task = tasks_list[4]
    verification_task = tasks_list[5]

    strategy_report_dict: dict[str, Any] = {}
    if hasattr(strategy_task, "output") and strategy_task.output:
        pydantic_obj = getattr(strategy_task.output, "pydantic", None)
        if isinstance(pydantic_obj, StrategyReport):
            strategy_report_dict = pydantic_obj.model_dump()
        elif hasattr(strategy_task.output, "to_dict"):
            strategy_report_dict = strategy_task.output.to_dict()

    verification_result_dict: dict[str, Any] = {}
    decision = "APPROVED"
    if hasattr(verification_task, "output") and verification_task.output:
        pydantic_obj = getattr(verification_task.output, "pydantic", None)
        if isinstance(pydantic_obj, VerificationResult):
            verification_result_dict = pydantic_obj.model_dump()
            decision = pydantic_obj.decision
        elif hasattr(verification_task.output, "to_dict"):
            verification_result_dict = verification_task.output.to_dict()
            decision = verification_result_dict.get("decision", "APPROVED")

    final_status = "completed" if decision == "APPROVED" else "verification_failed"

    return {
        "status": final_status,
        "decision": decision,
        "execution_time_seconds": duration,
        "strategy_report": strategy_report_dict,
        "verification_result": verification_result_dict,
        "agent_outputs": agent_outputs,
        "crew_raw_output": str(crew_output),
    }


def run_correction_crew(
    dataset_id: uuid.UUID,
    prior_agent_outputs: dict[str, str],
    audit_feedback: str,
    business_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Focused 2-agent self-correction crew: re-runs ONLY the Strategy and Verification agents
    incorporating exact discrepancy audit feedback to eliminate hallucinations.
    """
    start_time = time.time()
    logger.info("Executing self-correction loop for dataset: %s", dataset_id)

    tools = build_tools(dataset_id=dataset_id, db_session_factory=SessionLocal)
    llm = get_llm()
    agents_dict = create_retail_agents(tools=tools, business_profile=business_profile, llm=llm)

    strategy_agent = agents_dict["strategy"]
    verification_agent = agents_dict["verification"]

    # Construct context summary from prior agent outputs
    context_text = (
        f"Data Analyst Baseline:\n{prior_agent_outputs.get('data_analyst', '')[:1500]}\n\n"
        f"Marketing Findings:\n{prior_agent_outputs.get('marketing', '')[:1000]}\n\n"
        f"Finance Assessment:\n{prior_agent_outputs.get('finance', '')[:1000]}\n\n"
        f"Operations Review:\n{prior_agent_outputs.get('operations', '')[:1000]}\n"
    )

    from crewai import Task

    correction_strategy_task = Task(
        description=(
            "REVISE AND CORRECT the previous Strategy Report based on strict audit feedback.\n"
            f"Prior Domain Context:\n{context_text}\n\n"
            f"AUDIT FEEDBACK & DISCREPANCIES DETECTED:\n{audit_feedback}\n\n"
            "Instructions:\n"
            "1. Update the Strategy Report so that EVERY number matches the database ground truth exactly.\n"
            "2. Remove or correct any unsupported numbers flagged in the audit feedback.\n"
            "3. Update the claims list with the accurate ground-truth values.\n"
            "4. Retain all prioritized recommendations and action items.\n"
            "Return the corrected StrategyReport Pydantic object."
        ),
        expected_output="Corrected StrategyReport Pydantic object aligning 100% with ground-truth data.",
        agent=strategy_agent,
        output_pydantic=StrategyReport,
    )

    correction_verification_task = Task(
        description=(
            "Re-audit the revised Strategy Report against the database ground truth.\n"
            "Use `recompute_metric_tool` on all updated claims.\n"
            "Confirm whether all previous mismatches have been resolved.\n"
            "Set decision = 'APPROVED' if zero discrepancies remain, else 'REJECTED'."
        ),
        expected_output="VerificationResult Pydantic object detailing the audit of the corrected report.",
        agent=verification_agent,
        context=[correction_strategy_task],
        output_pydantic=VerificationResult,
    )

    correction_crew = Crew(
        agents=[strategy_agent, verification_agent],
        tasks=[correction_strategy_task, correction_verification_task],
        process=Process.sequential,
        verbose=True,
    )

    crew_output = correction_crew.kickoff(inputs={
        "dataset_period": "May 1, 2026 – October 31, 2026",
        "company_name": business_profile.get("company_name", "Retail Enterprise") if business_profile else "Retail Enterprise",
    })
    duration = round(time.time() - start_time, 2)

    strategy_report_dict: dict[str, Any] = {}
    if hasattr(correction_strategy_task, "output") and correction_strategy_task.output:
        pydantic_obj = getattr(correction_strategy_task.output, "pydantic", None)
        if isinstance(pydantic_obj, StrategyReport):
            strategy_report_dict = pydantic_obj.model_dump()
        elif hasattr(correction_strategy_task.output, "to_dict"):
            strategy_report_dict = correction_strategy_task.output.to_dict()

    verification_result_dict: dict[str, Any] = {}
    decision = "APPROVED"
    if hasattr(correction_verification_task, "output") and correction_verification_task.output:
        pydantic_obj = getattr(correction_verification_task.output, "pydantic", None)
        if isinstance(pydantic_obj, VerificationResult):
            verification_result_dict = pydantic_obj.model_dump()
            decision = pydantic_obj.decision
        elif hasattr(correction_verification_task.output, "to_dict"):
            verification_result_dict = correction_verification_task.output.to_dict()
            decision = verification_result_dict.get("decision", "APPROVED")

    return {
        "status": "completed" if decision == "APPROVED" else "verification_failed",
        "decision": decision,
        "execution_time_seconds": duration,
        "strategy_report": strategy_report_dict,
        "verification_result": verification_result_dict,
        "crew_raw_output": str(crew_output),
    }
