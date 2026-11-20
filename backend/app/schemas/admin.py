"""
app/schemas/admin.py
────────────────────
Pydantic request/response schemas for Admin APIs (Module 12).

All schemas use `from_attributes = True` so they can be constructed
directly from SQLAlchemy ORM objects via `model_validate(orm_obj)`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


# ─────────────────────────────────────────────────────────────────────────────
# User management
# ─────────────────────────────────────────────────────────────────────────────

class UserAdminView(BaseModel):
    """Full user record as returned to admins."""

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PatchRoleRequest(BaseModel):
    """Body for PATCH /admin/users/{id}/role."""

    role: Literal["admin", "manager", "analyst"] = Field(
        ...,
        description="New role to assign. Must be one of: admin, manager, analyst.",
    )


class PatchStatusRequest(BaseModel):
    """Body for PATCH /admin/users/{id}/status."""

    is_active: bool = Field(
        ...,
        description="True to activate the account; False to deactivate it.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Analysis admin view
# ─────────────────────────────────────────────────────────────────────────────

class AnalysisAdminView(BaseModel):
    """Analysis row as returned to admins (enriched with owner/dataset names)."""

    id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_name: str
    user_id: uuid.UUID | None
    triggered_by_email: str | None
    status: str
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: float | None   # derived: completed_at - started_at

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Report admin view
# ─────────────────────────────────────────────────────────────────────────────

class ReportAdminView(BaseModel):
    """Report row as returned to admins."""

    id: uuid.UUID
    analysis_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_name: str
    triggered_by_email: str | None
    title: str
    verification_status: str
    has_pdf: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Platform statistics
# ─────────────────────────────────────────────────────────────────────────────

class PlatformStats(BaseModel):
    """
    Aggregated platform statistics for the admin dashboard.

    All counts are computed with a single SQL query per category —
    no sequential Python loops over result sets.
    """

    # Users
    total_users: int
    active_users: int
    inactive_users: int
    users_by_role: dict[str, int]       # {"admin": 1, "manager": 3, "analyst": 12}

    # Datasets
    total_datasets: int
    datasets_last_30_days: int

    # Analyses
    total_analyses: int
    analyses_running: int
    analyses_completed: int
    analyses_failed: int
    analyses_verification_failed: int
    analyses_last_30_days: int
    avg_analysis_duration_seconds: float | None

    # Reports
    total_reports: int
    reports_verified: int
    reports_with_warnings: int
    reports_pdf_generated: int

    # Approvals
    total_approval_decisions: int
    approvals_approved: int
    approvals_rejected: int
    pending_recommendations: int        # recommendations awaiting decision

    # Chat
    total_chat_messages: int


# ─────────────────────────────────────────────────────────────────────────────
# Generic paginated wrapper
# ─────────────────────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    """Generic wrapper for any paginated admin list endpoint."""

    items: list
    total: int
    skip: int
    limit: int
    has_more: bool
