"""
app/models/user.py
───────────────────
User table — stores credentials, role, and status.

Roles:
  'admin'   – full system access
  'manager' – can approve recommendations, view all reports
  'analyst' – can upload datasets and trigger analyses
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """System user with role-based access control."""

    __tablename__ = "users"

    # ── Primary Key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Surrogate PK — UUID to avoid enumerable IDs in JWT",
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Login email (unique)",
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="bcrypt hash — never store plain text",
    )

    # ── Role ──────────────────────────────────────────────────────────────────
    role: Mapped[str] = mapped_column(
        Enum("admin", "manager", "analyst", name="user_role_enum"),
        nullable=False,
        default="analyst",
        server_default="analyst",
        comment="RBAC role",
    )

    # ── Status ────────────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
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
    business_profile: Mapped["BusinessProfile"] = relationship(  # type: ignore[name-defined]
        "BusinessProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    datasets: Mapped[list["Dataset"]] = relationship(  # type: ignore[name-defined]
        "Dataset", back_populates="owner", cascade="all, delete-orphan"
    )
    analyses: Mapped[list["Analysis"]] = relationship(  # type: ignore[name-defined]
        "Analysis", back_populates="triggered_by", cascade="all, delete-orphan"
    )
    approvals: Mapped[list["ApprovalHistory"]] = relationship(  # type: ignore[name-defined]
        "ApprovalHistory", back_populates="approver", cascade="all, delete-orphan"
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(  # type: ignore[name-defined]
        "ChatMessage", back_populates="user", cascade="all, delete-orphan"
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
