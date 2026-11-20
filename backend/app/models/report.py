"""
app/models/report.py
─────────────────────
Stores the final verified Business Intelligence Report.
One report per Analysis run (1-to-1).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Report(Base):
    """
    Final BI report produced after Verification Agent approval.

    - content_json : structured sections (dict) for frontend rendering
    - pdf_path     : path to the ReportLab-generated PDF on disk
    """

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── FK ────────────────────────────────────────────────────────────────────
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        unique=True,            # one report per analysis run
        nullable=False,
        index=True,
    )

    # ── Content ───────────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="Retail Business Intelligence Report",
    )
    content_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Structured report sections: executive_summary, kpis, findings, recommendations, …",
    )
    executive_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Plain-text executive summary (from Strategy Agent)"
    )

    # ── PDF ───────────────────────────────────────────────────────────────────
    pdf_path: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="Server-side absolute path to generated PDF",
    )

    # ── Verification ──────────────────────────────────────────────────────────
    verification_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        comment="approved | rejected | pending",
    )
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="report")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Report id={self.id} verification={self.verification_status}>"
