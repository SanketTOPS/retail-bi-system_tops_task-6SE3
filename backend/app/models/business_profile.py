"""
app/models/business_profile.py  (Module 3 — full replacement)
────────────────────────────────
One-to-one extension of User with rich business-specific metadata.

New fields added in Module 3:
  company_name   → renamed from business_name (old column dropped via migration)
  team_size      → positive integer
  business_goals → JSONB array of goal strings
  website        → optional URL
  phone          → optional phone number
  founded_year   → optional integer year
  logo_url       → optional image URL for the dashboard
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BusinessProfile(Base):
    """
    Business metadata attached to a User account (1-to-1).

    The ``unique=True`` on ``user_id`` enforces the one-profile-per-user
    constraint at the database level, complementing the application-level
    guard in the service layer.
    """

    __tablename__ = "business_profiles"
    __table_args__ = (
        Index("ix_bp_user_id", "user_id"),
        Index("ix_bp_industry", "industry"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── FK to users ───────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,            # DB-level 1-to-1 guard
        nullable=False,
    )

    # ── Core Business Info ────────────────────────────────────────────────────
    company_name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="Official company / business name",
    )
    industry: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Retail",
        server_default="Retail",
        comment="e.g. Retail, Healthcare, Banking, Manufacturing",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Short business description shown on the dashboard",
    )

    # ── Team & Scale ──────────────────────────────────────────────────────────
    team_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Total number of employees (must be > 0)",
    )

    # ── Strategic Goals (stored as a JSON array of strings) ───────────────────
    business_goals: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment='e.g. ["Increase revenue by 20%", "Reduce inventory waste"]',
    )

    # ── Location ──────────────────────────────────────────────────────────────
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(
        String(100), nullable=False, default="India", server_default="India"
    )

    # ── Contact / Web ─────────────────────────────────────────────────────────
    website: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Company website URL",
    )
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="URL to company logo used in PDF reports and dashboard header",
    )

    # ── History ───────────────────────────────────────────────────────────────
    founded_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Year the business was established (1800–current year)",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", back_populates="business_profile"
    )

    def __repr__(self) -> str:
        return (
            f"<BusinessProfile company={self.company_name!r} "
            f"industry={self.industry} team_size={self.team_size}>"
        )
