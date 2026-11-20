"""
app/models/__init__.py
───────────────────────
Convenience re-export so callers can do:
    from app.models import User, Dataset, Analysis, ...
Also ensures every model is imported (registered with Base.metadata)
before create_all() or Alembic autogenerate runs.
"""

from app.models.user import User                          # noqa: F401
from app.models.business_profile import BusinessProfile   # noqa: F401
from app.models.dataset import Dataset                    # noqa: F401
from app.models.analysis import Analysis, AgentLog        # noqa: F401
from app.models.report import Report                      # noqa: F401
from app.models.recommendation import Recommendation      # noqa: F401
from app.models.approval import ApprovalHistory           # noqa: F401
from app.models.chat_message import ChatMessage           # noqa: F401

# ── Retail data tables ────────────────────────────────────────────────────────
from app.models.retail import (                           # noqa: F401
    RetailCustomer,
    RetailProduct,
    RetailTransaction,
    RetailTransactionItem,
    RetailInventoryMovement,
    RetailExpense,
)

__all__ = [
    "User",
    "BusinessProfile",
    "Dataset",
    "Analysis",
    "AgentLog",
    "Report",
    "Recommendation",
    "ApprovalHistory",
    "ChatMessage",
    "RetailCustomer",
    "RetailProduct",
    "RetailTransaction",
    "RetailTransactionItem",
    "RetailInventoryMovement",
    "RetailExpense",
]
