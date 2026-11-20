"""
app/models/dataset.py
──────────────────────
Tracks each Excel file uploaded by a user.
After ingestion, row_counts stores per-sheet record counts as JSONB.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Dataset(Base):
    """
    Represents one uploaded Excel / CSV dataset file.

    Status lifecycle:
      pending → processing → ready | failed
    """

    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Ownership ─────────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── File Metadata ─────────────────────────────────────────────────────────
    original_filename: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Name as uploaded by user"
    )
    stored_filename: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="UUID-prefixed name on disk"
    )
    file_path: Mapped[str] = mapped_column(
        String(1000), nullable=False, comment="Absolute server-side path"
    )
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Ingestion ─────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        Enum("pending", "processing", "ready", "failed", name="dataset_status_enum"),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )
    row_counts: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment='e.g. {"Customers": 500, "Transactions": 3000}',
    )
    cleaning_summary: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment='Detailed cleaning statistics per sheet (before, after, duplicates, nulls, orphans)',
    )
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    owner: Mapped["User"] = relationship("User", back_populates="datasets")  # type: ignore[name-defined]
    analyses: Mapped[list["Analysis"]] = relationship(  # type: ignore[name-defined]
        "Analysis", back_populates="dataset", cascade="all, delete-orphan"
    )

    # ── Retail data children (all share dataset_id FK) ────────────────────────
    customers: Mapped[list["RetailCustomer"]] = relationship(  # type: ignore[name-defined]
        "RetailCustomer", back_populates="dataset", cascade="all, delete-orphan"
    )
    products: Mapped[list["RetailProduct"]] = relationship(  # type: ignore[name-defined]
        "RetailProduct", back_populates="dataset", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["RetailTransaction"]] = relationship(  # type: ignore[name-defined]
        "RetailTransaction", back_populates="dataset", cascade="all, delete-orphan"
    )
    inventory_movements: Mapped[list["RetailInventoryMovement"]] = relationship(  # type: ignore[name-defined]
        "RetailInventoryMovement", back_populates="dataset", cascade="all, delete-orphan"
    )
    expenses: Mapped[list["RetailExpense"]] = relationship(  # type: ignore[name-defined]
        "RetailExpense", back_populates="dataset", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Dataset id={self.id} file={self.original_filename} status={self.status}>"
