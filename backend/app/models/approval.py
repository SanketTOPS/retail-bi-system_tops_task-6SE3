"""
app/models/approval.py
───────────────────────
Audit trail of every approve/reject decision made by a manager.
Linked to Recommendation (the item being decided).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ApprovalHistory(Base):
    """
    Immutable audit record of a manager's decision on a Recommendation.
    One recommendation may have multiple history rows if re-submitted after rejection.
    """

    __tablename__ = "approval_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── FKs ───────────────────────────────────────────────────────────────────
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Manager who made the decision",
    )

    # ── Decision ──────────────────────────────────────────────────────────────
    decision: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="approved | rejected",
    )
    comment: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Optional manager comment explaining decision"
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    recommendation: Mapped["Recommendation"] = relationship(  # type: ignore[name-defined]
        "Recommendation", back_populates="approval_history"
    )
    approver: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", back_populates="approvals"
    )

    def __repr__(self) -> str:
        return f"<ApprovalHistory rec={self.recommendation_id} decision={self.decision}>"
