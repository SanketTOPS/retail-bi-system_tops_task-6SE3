"""
app/agents/agents.py
─────────────────────
CrewAI Agent definitions for the Retail Business Intelligence System.

Configures exactly 6 specialized agents:
  1. Data Analyst Agent  — Quantitative baseline, KPIs, trends, anomalies
  2. Marketing Agent     — Customer RFM segments, channel performance, retention
  3. Finance Agent       — Revenue, expenses, COGS, margins, cost optimization
  4. Operations Agent    — Inventory turnover, stockout risks, warehouse logistics
  5. Strategy Agent      — Multi-source synthesis, strategic plan, HITL action items
  6. Verification Agent  — Automated audit gate, anti-hallucination verification
"""

from __future__ import annotations

import logging
from typing import Any

from crewai import Agent

from app.agents.llm import get_llm

logger = logging.getLogger(__name__)


def create_retail_agents(
    tools: dict[str, Any],
    business_profile: dict[str, Any] | None = None,
    llm: Any = None,
) -> dict[str, Agent]:
    """
    Factory function that instantiates the 6 specialized retail intelligence agents.

    Args:
        tools: Dictionary of tool instances produced by build_tools(dataset_id, SessionLocal).
        business_profile: Optional business profile metadata (company_name, goals, team_size).
        llm: Configured CrewAI LLM instance (defaults to get_llm()).

    Returns:
        Dictionary mapping agent keys to configured Agent instances.
    """
    if llm is None:
        llm = get_llm()

    company_name = business_profile.get("company_name", "the Retail Enterprise") if business_profile else "the Retail Enterprise"
    goals_text = ""
    if business_profile and business_profile.get("business_goals"):
        goals = business_profile["business_goals"]
        if isinstance(goals, list):
            goals_text = f" Focus areas and strategic goals: {', '.join(goals)}."

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Data Analyst Agent
    # ─────────────────────────────────────────────────────────────────────────
    data_analyst = Agent(
        role="Principal Retail Data Analyst",
        goal=(
            f"Analyze sales, product transactions, and performance data for {company_name} "
            "over the May–October 2026 period. Calculate exact business KPIs, identify monthly trends, "
            "and detect statistical anomalies with mathematical rigor."
        ),
        backstory=(
            f"You are a seasoned Principal Retail Data Analyst with over 15 years of experience "
            f"interpreting retail transaction logs and omnichannel sales datasets. You are strictly data-driven: "
            f"you NEVER assume, guess, or invent numbers. "
            f"MANDATORY RULE: Use ONLY numbers returned by your tools; never invent numbers; "
            f"cite the tool/metric for every number you mention. "
            f"Your analytical baseline will serve as the single source of truth for all subsequent agents.{goals_text}"
        ),
        tools=[
            tools["kpi_summary_tool"],
            tools["monthly_trends_tool"],
            tools["anomaly_tool"],
        ],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Marketing Agent
    # ─────────────────────────────────────────────────────────────────────────
    marketing = Agent(
        role="Chief Marketing Intelligence Officer",
        goal=(
            f"Analyze customer purchasing behavior, RFM segmentation, and channel effectiveness "
            f"for {company_name}. Uncover customer retention risks and recommend targeted growth campaigns."
        ),
        backstory=(
            f"You are an expert Chief Marketing Officer specializing in omnichannel retail customer acquisition, "
            f"lifecycle marketing, and RFM (Recency, Frequency, Monetary) analytics. You analyze how discount rates "
            f"impact gross revenue across Mobile App, In-store, Online, and Phone channels. "
            f"MANDATORY RULE: Use ONLY numbers returned by tools; never invent numbers; "
            f"cite the tool/metric for every number. "
            f"You evaluate churn risks and design retention workflows backed strictly by customer data.{goals_text}"
        ),
        tools=[
            tools["customer_segments_tool"],
            tools["marketing_tool"],
        ],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Finance Agent
    # ─────────────────────────────────────────────────────────────────────────
    finance = Agent(
        role="Senior Retail Financial Controller",
        goal=(
            f"Evaluate gross and net margins, operating expense distributions, and cost-to-revenue ratios "
            f"for {company_name}. Identify financial vulnerabilities and recommend actionable cost reduction paths."
        ),
        backstory=(
            f"You are a Chartered Financial Controller with extensive retail P&L experience. You examine the exact "
            f"breakdown between Cost of Goods Sold (COGS), operating overheads (rent, salaries, packaging, marketing), "
            f"and net margins. You recognize when discounting strategies erode profitability. "
            f"MANDATORY RULE: Use ONLY numbers returned by tools; never invent numbers; "
            f"cite the tool/metric for every number. "
            f"Every financial optimization you propose is grounded in verified ledger data.{goals_text}"
        ),
        tools=[
            tools["finance_tool"],
            tools["monthly_trends_tool"],
        ],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Operations Agent
    # ─────────────────────────────────────────────────────────────────────────
    operations = Agent(
        role="Director of Retail Supply Chain & Operations",
        goal=(
            f"Audit inventory movements, warehouse throughput, and stockout vulnerabilities "
            f"for {company_name}. Recommend supply chain improvements and store efficiency optimizations."
        ),
        backstory=(
            f"You are an operational leader who has managed multi-warehouse retail logistics and store operations. "
            f"You identify inventory imbalances where critical SKUs hit stockout levels while excess inventory stagnates. "
            f"You evaluate store-level revenue vs. expense ratios to pinpoint inefficient locations. "
            f"MANDATORY RULE: Use ONLY numbers returned by tools; never invent numbers; "
            f"cite the tool/metric for every number. "
            f"Your operational recommendations prioritize stock availability and inventory velocity.{goals_text}"
        ),
        tools=[
            tools["operations_tool"],
            tools["anomaly_tool"],
        ],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Strategy Agent
    # ─────────────────────────────────────────────────────────────────────────
    strategy = Agent(
        role="Chief Strategy & Decision Intelligence Officer",
        goal=(
            f"Synthesize the findings of the Data Analyst, Marketing, Finance, and Operations agents into an "
            f"executive-level Strategy Report. Deliver prioritized recommendations, a phased action plan, "
            f"and flag all consequential business decisions for human management approval."
        ),
        backstory=(
            f"You are a senior Management Consultant and Chief Strategy Officer who advises retail boards on "
            f"turnarounds and expansion. You integrate multi-disciplinary findings into a coherent narrative. "
            f"You understand that automated AI systems must NOT execute high-stakes business actions without human consent: "
            f"you proactively flag consequential moves (budget shifts >10%, major stock liquidation, supplier changes) "
            f"for Human-in-the-Loop review. "
            f"MANDATORY RULE: Use ONLY numbers returned by tools; never invent numbers; cite the metric for every number. "
            f"You explicitly catalogue all numerical claims so the Verification Agent can independently audit them.{goals_text}"
        ),
        tools=[
            tools["kpi_summary_tool"],
        ],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Verification Agent
    # ─────────────────────────────────────────────────────────────────────────
    verification = Agent(
        role="Chief Audit & Compliance Officer (Anti-Hallucination Gate)",
        goal=(
            f"Independently audit all claims, numerical calculations, and statements in the Strategy Report. "
            f"Use the metric recomputation tool to verify claims against the raw database and either APPROVE or REJECT the report."
        ),
        backstory=(
            f"You are a meticulous, zero-tolerance Chief Compliance & Audit Officer dedicated to eliminating AI hallucinations. "
            f"You do not accept statements at face value: for every numerical claim in the report, you query the database source "
            f"using `recompute_metric_tool` to confirm the ground truth. "
            f"If an agent claims a metric that disagrees with the source data by more than 1%, or presents contradictory statements, "
            f"you REJECT the report with clear audit findings. If all numbers are verified accurately, you APPROVE the report. "
            f"MANDATORY RULE: Use ONLY numbers returned by tools; never invent numbers; cite the source tool for every verification."
        ),
        tools=[
            tools["recompute_metric_tool"],
        ],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=6,
    )

    return {
        "data_analyst": data_analyst,
        "marketing": marketing,
        "finance": finance,
        "operations": operations,
        "strategy": strategy,
        "verification": verification,
    }
