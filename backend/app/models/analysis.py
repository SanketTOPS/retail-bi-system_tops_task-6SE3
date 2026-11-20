"""
app/models/analysis.py
───────────────────────
Tracks a full CrewAI analysis run and individual agent execution logs.

AnalysisRun  → one record per "Run Analysis" button click
AgentLog     → one record per agent execution within a run
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Analysis(Base):
    """
    Represents one complete multi-agent analysis execution.

    Status lifecycle:
      queued → running → completed | failed | verification_failed
    """

    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Foreign Keys ──────────────────────────────────────────────────────────
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Who triggered the analysis",
    )

    # ── Status ────────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        Enum(
            "queued",
            "running",
            "completed",
            "failed",
            "verification_failed",
            name="analysis_status_enum",
        ),
        nullable=False,
        default="queued",
        server_default="queued",
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # ── Summary KPIs (snapshot stored for quick dashboard read) ───────────────
    kpi_snapshot: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Key metrics at time of analysis — avoids re-computing for dashboard",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="analyses")  # type: ignore[name-defined]
    triggered_by: Mapped["User"] = relationship("User", back_populates="analyses")  # type: ignore[name-defined]
    agent_logs: Mapped[list["AgentLog"]] = relationship(
        "AgentLog", back_populates="analysis", cascade="all, delete-orphan",
        order_by="AgentLog.started_at",
    )
    report: Mapped["Report"] = relationship(  # type: ignore[name-defined]
        "Report", back_populates="analysis", uselist=False, cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(  # type: ignore[name-defined]
        "Recommendation", back_populates="analysis", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Analysis id={self.id} status={self.status}>"


class AgentLog(Base):
    """
    Per-agent execution log within an Analysis run.
    Records timing, input context, raw output, and token usage.
    """

    __tablename__ = "agent_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── FK ────────────────────────────────────────────────────────────────────
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Agent Identity ────────────────────────────────────────────────────────
    agent_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="e.g. data_analyst, marketing, finance, operations, strategy, verification",
    )
    sequence_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Execution order within the crew run (0-based)",
    )

    # ── Execution ─────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        Enum("pending", "running", "completed", "failed", name="agent_status_enum"),
        nullable=False,
        default="pending",
        index=True,
    )
    input_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Truncated task description sent to agent"
    )
    raw_output: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Full agent response text"
    )
    output_structured: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Parsed JSON output if agent returns structured data"
    )
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Performance ───────────────────────────────────────────────────────────
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="agent_logs")

    def __repr__(self) -> str:
        return f"<AgentLog agent={self.agent_name} status={self.status}>"
