"""
app/services/chat_service.py
─────────────────────────────
Service handling Business AI conversational intelligence.

Guarantees:
  1. Data Grounding: Agent has direct access to the 8 analytics tools via server-side closure.
  2. Domain Guardrails: Strictly refuses or redirects non-business questions.
  3. Anti-Hallucination: Explicitly instructed to state "Data not available in this dataset" rather than guess.
  4. Context Continuity: Maintains the last 6 messages (3 conversation turns) and incorporates the latest verified BI report.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from crewai import Agent, Crew, Process, Task
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.agents.llm import get_llm
from app.agents.tools import build_tools
from app.core.database import SessionLocal
from app.main import AppException
from app.models.analysis import Analysis
from app.models.chat_message import ChatMessage
from app.models.dataset import Dataset
from app.models.report import Report
from app.models.user import User

logger = logging.getLogger(__name__)


def get_chat_history(
    db: Session,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> tuple[Sequence[ChatMessage], int]:
    """Retrieves paginated chat history for the user in chronological order."""
    total_stmt = select(ChatMessage).where(ChatMessage.user_id == user_id)
    total_count = len(db.execute(total_stmt).scalars().all())

    stmt = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    messages = db.execute(stmt).scalars().all()
    return messages, total_count


def get_recent_conversation_context(
    db: Session,
    user_id: uuid.UUID,
    max_messages: int = 6,
) -> list[dict[str, str]]:
    """Fetches the last N messages formatted for prompt injection."""
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(max_messages)
    )
    rows = list(db.execute(stmt).scalars().all())
    rows.reverse()  # Chronological order
    return [{"role": r.role, "content": r.content} for r in rows]


def resolve_analysis_context(
    db: Session,
    user: User,
    analysis_id: uuid.UUID | None = None,
) -> tuple[Analysis | None, Report | None, uuid.UUID | None]:
    """
    Finds the active or most recent verified analysis to anchor the conversation context.
    """
    if analysis_id:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            raise AppException(status_code=404, detail="Specified analysis context not found", code="ANALYSIS_NOT_FOUND")
    else:
        # Default to latest completed analysis for this user (or platform if admin)
        stmt = select(Analysis).where(Analysis.status == "completed")
        if user.role != "admin":
            stmt = stmt.where(Analysis.user_id == user.id)
        stmt = stmt.order_by(Analysis.completed_at.desc()).limit(1)
        analysis = db.execute(stmt).scalar_one_or_none()

    if not analysis:
        # Check if there is any dataset available at all
        d_stmt = select(Dataset).where(Dataset.status == "ready").order_by(Dataset.uploaded_at.desc()).limit(1)
        dataset = db.execute(d_stmt).scalar_one_or_none()
        dataset_id = dataset.id if dataset else None
        return None, None, dataset_id

    report = db.query(Report).filter(Report.analysis_id == analysis.id).first()
    return analysis, report, analysis.dataset_id


def process_chat_message(
    db: Session,
    user: User,
    message: str,
    analysis_id: uuid.UUID | None = None,
) -> tuple[ChatMessage, ChatMessage, uuid.UUID | None]:
    """
    Core chat orchestrator:
      1. Resolves analysis context & dataset_id.
      2. Retrieves conversation memory (last 6 messages).
      3. Constructs Business Q&A Agent with grounded tools.
      4. Executes single-turn response.
      5. Saves user and assistant messages in database.
    """
    logger.info("Processing chat inquiry from user %s (%s)", user.id, user.email)

    # 1. Resolve context
    analysis, report, dataset_id = resolve_analysis_context(db, user, analysis_id)
    recent_history = get_recent_conversation_context(db, user.id, max_messages=6)

    # 2. Prepare conversation memory block
    history_text = ""
    if recent_history:
        history_lines = [f"{msg['role'].upper()}: {msg['content']}" for msg in recent_history]
        history_text = "Recent Conversation History:\n" + "\n".join(history_lines) + "\n\n"

    # 3. Prepare verified report context block
    report_context_text = ""
    if report and report.content_json:
        rj = report.content_json
        exec_summary = rj.get("executive_summary", "")
        insights = "\n".join([f"- {i}" for i in rj.get("performance_insights", [])[:4]])
        report_context_text = (
            f"Latest Verified Business Intelligence Report Context:\n"
            f"Title: {report.title} (Verification: {report.verification_status})\n"
            f"Executive Summary: {exec_summary[:600]}\n"
            f"Key Performance Insights:\n{insights}\n\n"
        )

    # 4. If no dataset exists yet, provide standard helpful guidance
    if not dataset_id:
        reply_text = (
            "No business dataset has been uploaded to the system yet. "
            "Please navigate to the **Dataset Upload** page and upload your May–October 2026 retail Excel file "
            "so I can analyze your sales, inventory, expenses, and customer performance."
        )
    else:
        # Build tools bound to this dataset
        tools_dict = build_tools(dataset_id=dataset_id, db_session_factory=SessionLocal)
        llm = get_llm()

        # 5. Create specialized Business Intelligence Q&A Agent
        qa_agent = Agent(
            role="Retail Decision Intelligence Advisor",
            goal=(
                "Answer executive and operational questions accurately using only verified business data, "
                "analytics tools, and verified intelligence reports."
            ),
            backstory=(
                "You are an expert Retail Decision Intelligence Advisor specializing in retail business operations, "
                "sales performance, customer behavior, and financial profitability.\n"
                "STRICT GUARDRAILS:\n"
                "1. DOMAIN BOUNDARY: You exclusively address business, retail, financial, inventory, and operational topics. "
                "If the user asks questions about unrelated topics (e.g., general trivia, jokes, coding, sports, creative writing), "
                "politely refuse and redirect them to retail business operations.\n"
                "2. GROUNDED IN DATA: Use ONLY numbers returned by your analytical tools or explicitly stated in the verified report context. "
                "NEVER invent, estimate, or hallucinate numbers.\n"
                "3. ABSENCE OF DATA: If the user asks for metrics not tracked in this dataset (e.g. competitor pricing, market share, 2027 forecasts), "
                "explicitly state: 'Data not available in this dataset' rather than guessing.\n"
                "4. CONCISE & PROFESSIONAL: Provide clear, executive-ready answers with bullet points where appropriate."
            ),
            tools=list(tools_dict.values()),
            llm=llm,
            verbose=False,
            max_iter=4,
        )

        task_prompt = (
            f"{history_text}"
            f"{report_context_text}"
            f"User Inquiry:\n\"{message}\"\n\n"
            "Instructions:\n"
            "- If answering this inquiry requires quantitative data (e.g., revenue, return rate, profit, channel breakdown, stockouts), "
            "call the appropriate tool to retrieve the exact figures.\n"
            "- Strictly obey your domain guardrail (redirect non-business questions) and anti-hallucination guardrail.\n"
            "- Respond in professional Markdown format."
        )

        qa_task = Task(
            description=task_prompt,
            expected_output="A data-grounded, professional business answer strictly citing verified metrics.",
            agent=qa_agent,
        )

        try:
            crew = Crew(agents=[qa_agent], tasks=[qa_task], process=Process.sequential, verbose=False)
            crew_result = crew.kickoff()
            reply_text = str(crew_result).strip()
        except Exception as exc:
            logger.error("Chat agent execution failed: %s", exc, exc_info=True)
            reply_text = (
                "I encountered an error accessing the analytical tools. "
                "Please verify that the dataset is ready and try again in a moment."
            )

    # 6. Save messages to database
    now = datetime.now(timezone.utc)
    current_analysis_id = analysis.id if analysis else None

    user_msg = ChatMessage(
        user_id=user.id,
        role="user",
        content=message,
        analysis_id=current_analysis_id,
        created_at=now,
    )
    assistant_msg = ChatMessage(
        user_id=user.id,
        role="assistant",
        content=reply_text,
        analysis_id=current_analysis_id,
        created_at=now,
    )

    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)

    return user_msg, assistant_msg, dataset_id
