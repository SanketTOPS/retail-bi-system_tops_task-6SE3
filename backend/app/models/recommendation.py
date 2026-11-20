"""
app/models/recommendation.py
──────────────────────────────
Individual actionable recommendations produced by the Strategy Agent,
each with its own approval status (Human-in-the-Loop gate).

Lifecycle:
  pending → approved | rejected
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Recommendation(Base):
    """
    One business recommendation from the Strategy Agent output.

    approval_required=True  → manager must approve before action is logged.
    approval_required=False → informational; recorded automatically.
    """

    __tablename__ = "recommendations"

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

    # ── Recommendation Content ────────────────────────────────────────────────
    agent_name: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Which agent generated this recommendation",
    )
    category: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="e.g. Marketing, Finance, Operations, Strategy",
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expected_impact: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Quantified expected benefit"
    )

    # ── Priority (1=Critical, 2=High, 3=Medium, 4=Low) ───────────────────────
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3
    )

    # ── Human-in-the-Loop Gate ────────────────────────────────────────────────
    approval_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="True for consequential actions (budget changes, inventory orders)",
    )
    approval_status: Mapped[str] = mapped_column(
        Enum("pending", "approved", "rejected", name="approval_status_enum"),
        nullable=False,
        default="pending",
        index=True,
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    analysis: Mapped["Analysis"] = relationship(  # type: ignore[name-defined]
        "Analysis", back_populates="recommendations"
    )
    approval_history: Mapped[list["ApprovalHistory"]] = relationship(  # type: ignore[name-defined]
        "ApprovalHistory", back_populates="recommendation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Recommendation title={self.title!r} approval={self.approval_status}>"
