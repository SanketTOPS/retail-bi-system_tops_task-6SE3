"""
app/models/retail.py
─────────────────────
SQLAlchemy ORM models for the Retail dataset (03_Retail.xlsx).

Sheets → Tables:
  Customers            → retail_customers
  Products             → retail_products
  Transactions         → retail_transactions
  Transaction_Items    → retail_transaction_items
  Inventory_Movements  → retail_inventory_movements
  Expenses             → retail_expenses

Design rules:
  1. Every table has a dataset_id FK → datasets.id  (supports multi-upload isolation)
  2. Original source IDs (customer_id, product_id, etc.) are stored as VARCHAR
     because they come from Excel strings like 'CUS00001'.
  3. Composite unique constraints on (dataset_id + source_id) prevent duplicate
     ingestion of the same row across re-uploads.
  4. Monetary columns use Numeric(15, 2) for financial precision.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ─────────────────────────────────────────────────────────────────────────────
# 1. RetailCustomer
# ─────────────────────────────────────────────────────────────────────────────
class RetailCustomer(Base):
    """
    Mirrors the Customers sheet.
    customer_segment values: Regular | Premium | VIP
    """

    __tablename__ = "retail_customers"
    __table_args__ = (
        UniqueConstraint("dataset_id", "customer_id", name="uq_retail_customer_per_dataset"),
        Index("ix_retail_customers_segment", "customer_segment"),
        Index("ix_retail_customers_city", "city"),
        Index("ix_retail_customers_dataset", "dataset_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── Dataset Isolation FK ──────────────────────────────────────────────────
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Source Columns (from Excel) ───────────────────────────────────────────
    customer_id: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="e.g. CUS00001"
    )
    customer_name: Mapped[str] = mapped_column(String(300), nullable=False)
    city: Mapped[str | None] = mapped_column(String(150), nullable=True)
    signup_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    customer_segment: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Regular | Premium | VIP"
    )
    email: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # ── Ingestion Timestamp ───────────────────────────────────────────────────
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="customers")  # type: ignore[name-defined]
    transactions: Mapped[list["RetailTransaction"]] = relationship(
        "RetailTransaction",
        primaryjoin="and_(RetailCustomer.customer_id == foreign(RetailTransaction.customer_id),"
                    "RetailCustomer.dataset_id == foreign(RetailTransaction.dataset_id))",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<RetailCustomer {self.customer_id} segment={self.customer_segment}>"


# ─────────────────────────────────────────────────────────────────────────────
# 2. RetailProduct
# ─────────────────────────────────────────────────────────────────────────────
class RetailProduct(Base):
    """
    Mirrors the Products sheet.
    Profit margin per unit = unit_price - unit_cost
    """

    __tablename__ = "retail_products"
    __table_args__ = (
        UniqueConstraint("dataset_id", "product_id", name="uq_retail_product_per_dataset"),
        Index("ix_retail_products_category", "category"),
        Index("ix_retail_products_dataset", "dataset_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )

    # ── Source Columns ────────────────────────────────────────────────────────
    product_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="e.g. PRD0001")
    product_name: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="e.g. Electronics, Home, Clothing"
    )
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    reorder_level: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Minimum stock quantity before reorder"
    )
    supplier_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="products")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<RetailProduct {self.product_id} {self.product_name!r}>"


# ─────────────────────────────────────────────────────────────────────────────
# 3. RetailTransaction
# ─────────────────────────────────────────────────────────────────────────────
class RetailTransaction(Base):
    """
    Mirrors the Transactions sheet.
    One transaction has multiple line items in RetailTransactionItem.
    order_status values: Completed | Cancelled | Returned | Pending
    channel values: In-store | Mobile App | Online | Phone
    payment_method values: Card | UPI | Cash | Net Banking
    """

    __tablename__ = "retail_transactions"
    __table_args__ = (
        UniqueConstraint("dataset_id", "transaction_id", name="uq_retail_txn_per_dataset"),
        Index("ix_retail_txn_date", "transaction_date"),
        Index("ix_retail_txn_customer", "customer_id"),
        Index("ix_retail_txn_store", "store_id"),
        Index("ix_retail_txn_status", "order_status"),
        Index("ix_retail_txn_channel", "channel"),
        Index("ix_retail_txn_dataset", "dataset_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )

    # ── Source Columns ────────────────────────────────────────────────────────
    transaction_id: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="e.g. TRX00001"
    )
    customer_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    transaction_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    store_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    channel: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="In-store | Mobile App | Online | Phone"
    )
    gross_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    discount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    net_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, comment="gross_amount - discount"
    )
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    order_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Completed | Cancelled | Returned | Pending"
    )

    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="transactions")  # type: ignore[name-defined]
    items: Mapped[list["RetailTransactionItem"]] = relationship(
        "RetailTransactionItem", back_populates="transaction", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<RetailTransaction {self.transaction_id} net={self.net_amount}>"


# ─────────────────────────────────────────────────────────────────────────────
# 4. RetailTransactionItem
# ─────────────────────────────────────────────────────────────────────────────
class RetailTransactionItem(Base):
    """
    Mirrors the Transaction_Items sheet.
    Each row is one product line within a transaction.
    line_total = quantity × unit_price
    """

    __tablename__ = "retail_transaction_items"
    __table_args__ = (
        UniqueConstraint("dataset_id", "line_item_id", name="uq_retail_line_per_dataset"),
        Index("ix_retail_items_txn", "transaction_id"),
        Index("ix_retail_items_product", "product_id"),
        Index("ix_retail_items_dataset", "dataset_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )

    # ── Source Columns ────────────────────────────────────────────────────────
    line_item_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="e.g. LIN000001")
    transaction_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Links to retail_transactions.transaction_id (same dataset_id)",
    )
    product_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    line_total: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)

    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── ORM-level FK relationship via PKs ─────────────────────────────────────
    # We join through the UUID PK of RetailTransaction for ORM convenience
    transaction_pk: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retail_transactions.id", ondelete="CASCADE"),
        nullable=True,
        comment="ORM convenience FK to retail_transactions.id PK",
    )

    transaction: Mapped["RetailTransaction | None"] = relationship(
        "RetailTransaction", back_populates="items", foreign_keys=[transaction_pk]
    )

    def __repr__(self) -> str:
        return f"<RetailTransactionItem {self.line_item_id} qty={self.quantity} total={self.line_total}>"


# ─────────────────────────────────────────────────────────────────────────────
# 5. RetailInventoryMovement
# ─────────────────────────────────────────────────────────────────────────────
class RetailInventoryMovement(Base):
    """
    Mirrors the Inventory_Movements sheet.
    movement_type values: Sale | Return | Restock | Adjustment | Transfer
    """

    __tablename__ = "retail_inventory_movements"
    __table_args__ = (
        UniqueConstraint("dataset_id", "movement_id", name="uq_retail_inv_per_dataset"),
        Index("ix_retail_inv_product", "product_id"),
        Index("ix_retail_inv_date", "movement_date"),
        Index("ix_retail_inv_type", "movement_type"),
        Index("ix_retail_inv_warehouse", "warehouse_id"),
        Index("ix_retail_inv_dataset", "dataset_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Source Columns ────────────────────────────────────────────────────────
    movement_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="e.g. MOV00001")
    product_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    movement_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    movement_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Sale | Return | Restock | Adjustment | Transfer"
    )
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warehouse_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_no: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Links to transaction_id or other source doc"
    )

    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    dataset: Mapped["Dataset"] = relationship(  # type: ignore[name-defined]
        "Dataset", back_populates="inventory_movements"
    )

    def __repr__(self) -> str:
        return f"<RetailInventoryMovement {self.movement_id} type={self.movement_type}>"


# ─────────────────────────────────────────────────────────────────────────────
# 6. RetailExpense
# ─────────────────────────────────────────────────────────────────────────────
class RetailExpense(Base):
    """
    Mirrors the Expenses sheet.
    category values: Utilities | Packaging | Salaries | Marketing | Maintenance | Rent | …
    """

    __tablename__ = "retail_expenses"
    __table_args__ = (
        UniqueConstraint("dataset_id", "expense_id", name="uq_retail_exp_per_dataset"),
        Index("ix_retail_exp_date", "expense_date"),
        Index("ix_retail_exp_category", "category"),
        Index("ix_retail_exp_store", "store_id"),
        Index("ix_retail_exp_dataset", "dataset_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Source Columns ────────────────────────────────────────────────────────
    expense_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="e.g. REX0001")
    expense_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    store_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    category: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Utilities | Packaging | Salaries | …"
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(300), nullable=True)

    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    dataset: Mapped["Dataset"] = relationship(  # type: ignore[name-defined]
        "Dataset", back_populates="expenses"
    )

    def __repr__(self) -> str:
        return f"<RetailExpense {self.expense_id} cat={self.category} amt={self.amount}>"
