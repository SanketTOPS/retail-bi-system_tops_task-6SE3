"""
app/routers/admin.py
────────────────────
Admin-only Management APIs — Module 12

Responsibilities:
  - User management   : list, change role, activate/deactivate
  - Analysis oversight: list all analyses with status/owner filters
  - Report oversight  : list all generated reports
  - Platform stats    : aggregated counts and health metrics

Design Decisions:
  1. **Admin-only guard on every endpoint**
     All routes depend on `Depends(require_roles("admin"))`.  A non-admin
     JWT will get HTTP 403 before any DB query runs.

  2. **Pagination via skip/limit**
     Standard cursor-free pagination.  `skip` defaults to 0, `limit` to 20
     (max 200).  Every list response includes `total`, `has_more`, `skip`,
     `limit` so clients can build paginated UIs without an extra COUNT call
     (we do a cheap subquery COUNT alongside the data query).

  3. **Self-demotion protection**
     An admin cannot change their own role or deactivate their own account —
     this would lock them out of the system with no recovery path.

  4. **Stats with a single aggregation query per domain**
     The `/admin/stats` endpoint uses SQLAlchemy `func.count()` + `case()`
     expressions evaluated in one round-trip per table rather than N queries
     or Python-level counting of full result sets.

  5. **Filters are optional query params, not path segments**
     e.g., `GET /admin/analyses?status=failed&user_id=<uuid>`.  This keeps
     the URL clean and allows arbitrary filter combinations without a
     combinatorial explosion of path patterns.

Viva Question: Why is admin role checked via a dependency and not in-route?
Answer: Dependency injection runs before the route function body. If the user
is not an admin, FastAPI short-circuits and returns 403 without deserializing
the DB session, running any query, or touching any business logic. This reduces
attack surface and keeps authorization separate from business logic (SRP).
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.main import AppException
from app.models.analysis import Analysis
from app.models.approval import ApprovalHistory
from app.models.dataset import Dataset
from app.models.recommendation import Recommendation
from app.models.report import Report
from app.models.user import User
from app.schemas.admin import (
    AnalysisAdminView,
    PatchRoleRequest,
    PatchStatusRequest,
    PlatformStats,
    ReportAdminView,
    UserAdminView,
)
from app.utils.deps import get_current_active_user, require_roles

logger = logging.getLogger("retail_bi.admin")

router = APIRouter(prefix="/admin", tags=["Admin"])

# Shorthand dependency — every route in this file requires admin role
AdminOnly = Depends(require_roles("admin"))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _paginate(stmt, db: Session, skip: int, limit: int):
    """
    Execute a paginated SELECT and return (items, total_count).

    Runs two queries:
      1. COUNT(*) using the same WHERE conditions (no LIMIT).
      2. The data query with OFFSET skip LIMIT limit.

    Design: Wrapping the WHERE conditions in a subquery for COUNT ensures the
    total reflects filters, not the entire table.
    """
    # Total count (without offset/limit)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = db.scalar(count_stmt) or 0

    # Data page
    rows = db.execute(stmt.offset(skip).limit(limit)).all()
    return rows, total


def _clamp_limit(limit: int) -> int:
    """Prevent absurdly large pages that could OOM the process."""
    return min(max(limit, 1), 200)


# ─────────────────────────────────────────────────────────────────────────────
# 1. GET /admin/users
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/users",
    summary="[Admin] List all users",
    response_description="Paginated list of all system users",
    status_code=status.HTTP_200_OK,
)
def list_users(
    skip: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=20, ge=1, le=200, description="Max results (1–200)"),
    role: str | None = Query(default=None, description="Filter by role: admin|manager|analyst"),
    is_active: bool | None = Query(default=None, description="Filter by active status"),
    search: str | None = Query(default=None, description="Search by name or email (case-insensitive)"),
    db: Session = Depends(get_db),
    _admin: User = AdminOnly,
) -> dict:
    """
    Returns every user in the system with their role, status, and timestamps.

    **Filters (all optional, combinable):**
    - `role`      — exact match on user_role_enum value
    - `is_active` — boolean filter
    - `search`    — ILIKE match on `email` OR `full_name`

    **Sorted by:** `created_at DESC` (newest registrations first).

    Design: The search filter uses `ILIKE` (case-insensitive LIKE) which is
    index-friendly in PostgreSQL when combined with a pg_trgm trigram index
    (not added here for simplicity, but straightforward to add in Alembic).
    """
    limit = _clamp_limit(limit)
    stmt = select(User).order_by(User.created_at.desc())

    if role is not None:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            User.email.ilike(pattern) | User.full_name.ilike(pattern)
        )

    rows, total = _paginate(stmt, db, skip, limit)
    users = [row[0] for row in rows]

    items = [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "updated_at": u.updated_at.isoformat() if u.updated_at else None,
        }
        for u in users
    ]

    logger.info("Admin listed %d users (total=%d)", len(items), total)
    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": (skip + len(items)) < total,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. PATCH /admin/users/{id}/role
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/users/{user_id}/role",
    summary="[Admin] Change a user's role",
    response_description="Updated user record",
    status_code=status.HTTP_200_OK,
)
def patch_user_role(
    user_id: uuid.UUID,
    body: PatchRoleRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles("admin")),
) -> dict:
    """
    Changes the RBAC role of any user.

    **Guards:**
    - Admin cannot change their own role (self-demotion prevention).
    - Target user must exist (404 if not found).
    - New role must be one of `admin | manager | analyst`.

    **Why prevent self-role change?**
    If the only admin demotes themselves to `analyst`, the system would have
    zero admins — a unrecoverable state. Postgres-level constraint is not
    practical here (would need a trigger), so we enforce it in application code.

    After the change the user's next JWT will carry the old role until it
    expires (stateless JWT design). For immediate effect, the user must
    re-authenticate.
    """
    if str(user_id) == str(current_admin.id):
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admins cannot change their own role. Ask another admin.",
            code="SELF_ROLE_CHANGE_FORBIDDEN",
        )

    target = db.get(User, user_id)
    if not target:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
            code="USER_NOT_FOUND",
        )

    old_role = target.role
    target.role = body.role
    db.commit()
    db.refresh(target)

    logger.info(
        "Admin %s changed user %s role: %s → %s",
        current_admin.email,
        target.email,
        old_role,
        body.role,
    )

    return {
        "success": True,
        "message": f"Role updated from '{old_role}' to '{body.role}'.",
        "data": {
            "id": str(target.id),
            "email": target.email,
            "full_name": target.full_name,
            "role": target.role,
            "is_active": target.is_active,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. PATCH /admin/users/{id}/status
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/users/{user_id}/status",
    summary="[Admin] Activate or deactivate a user account",
    response_description="Updated user active status",
    status_code=status.HTTP_200_OK,
)
def patch_user_status(
    user_id: uuid.UUID,
    body: PatchStatusRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles("admin")),
) -> dict:
    """
    Activates or deactivates a user account.

    **Deactivated users:**
    - Cannot log in (the `get_current_active_user` dependency raises 400
      "Inactive user" for any JWT belonging to a deactivated account).
    - Existing active JWT tokens remain valid until expiry (stateless design).
      To force immediate logout, reduce `ACCESS_TOKEN_EXPIRE_MINUTES` or
      implement a token-revocation blocklist (out of scope here).

    **Guards:**
    - Admin cannot deactivate their own account (self-lockout prevention).

    Design: `is_active` is a boolean flag on the User record checked on every
    authenticated request via `get_current_active_user`. This is O(1) per
    request and requires no token blacklist.
    """
    if str(user_id) == str(current_admin.id):
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admins cannot change their own account status.",
            code="SELF_STATUS_CHANGE_FORBIDDEN",
        )

    target = db.get(User, user_id)
    if not target:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
            code="USER_NOT_FOUND",
        )

    if target.is_active == body.is_active:
        action = "active" if body.is_active else "inactive"
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User is already {action}. No change made.",
            code="STATUS_ALREADY_SET",
        )

    old_status = target.is_active
    target.is_active = body.is_active
    db.commit()
    db.refresh(target)

    action_word = "activated" if body.is_active else "deactivated"
    logger.info(
        "Admin %s %s user %s (was_active=%s)",
        current_admin.email,
        action_word,
        target.email,
        old_status,
    )

    return {
        "success": True,
        "message": f"User account {action_word} successfully.",
        "data": {
            "id": str(target.id),
            "email": target.email,
            "full_name": target.full_name,
            "role": target.role,
            "is_active": target.is_active,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. GET /admin/analyses
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/analyses",
    summary="[Admin] List all analyses across all users",
    response_description="Paginated, filterable list of every analysis run",
    status_code=status.HTTP_200_OK,
)
def list_all_analyses(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Filter by status: queued|running|completed|failed|verification_failed",
    ),
    user_id: uuid.UUID | None = Query(default=None, description="Filter by triggering user UUID"),
    dataset_id: uuid.UUID | None = Query(default=None, description="Filter by dataset UUID"),
    from_date: datetime | None = Query(default=None, description="Filter: started_at ≥ this ISO datetime"),
    to_date: datetime | None = Query(default=None, description="Filter: started_at ≤ this ISO datetime"),
    db: Session = Depends(get_db),
    _admin: User = AdminOnly,
) -> dict:
    """
    Returns ALL analysis runs (across all users and datasets) with enriched
    owner and dataset metadata.

    **Filter parameters (all optional, combinable):**
    | Param        | Type     | Description                              |
    |--------------|----------|------------------------------------------|
    | `status`     | string   | Exact match on analysis status enum      |
    | `user_id`    | UUID     | Analyses triggered by a specific user    |
    | `dataset_id` | UUID     | Analyses on a specific dataset           |
    | `from_date`  | datetime | `started_at` ≥ ISO 8601 datetime         |
    | `to_date`    | datetime | `started_at` ≤ ISO 8601 datetime         |

    **Performance note:** JOINs to `datasets` and `users` are needed for
    `dataset_name` and `triggered_by_email`.  These are small reference
    tables, so the join cost is negligible.  For a system with millions of
    analyses, add a composite index on `(status, started_at DESC)`.
    """
    limit = _clamp_limit(limit)

    stmt = (
        select(Analysis, Dataset, User)
        .join(Dataset, Analysis.dataset_id == Dataset.id)
        .outerjoin(User, Analysis.user_id == User.id)
        .order_by(Analysis.started_at.desc())
    )

    if status_filter:
        stmt = stmt.where(Analysis.status == status_filter)
    if user_id:
        stmt = stmt.where(Analysis.user_id == user_id)
    if dataset_id:
        stmt = stmt.where(Analysis.dataset_id == dataset_id)
    if from_date:
        stmt = stmt.where(Analysis.started_at >= from_date)
    if to_date:
        stmt = stmt.where(Analysis.started_at <= to_date)

    rows, total = _paginate(stmt, db, skip, limit)

    items = []
    for analysis, dataset, user in rows:
        # Derive duration in seconds (None if still running)
        duration: float | None = None
        if analysis.completed_at and analysis.started_at:
            duration = (analysis.completed_at - analysis.started_at).total_seconds()

        items.append({
            "id": str(analysis.id),
            "dataset_id": str(analysis.dataset_id),
            "dataset_name": dataset.name if dataset else "—",
            "user_id": str(analysis.user_id) if analysis.user_id else None,
            "triggered_by_email": user.email if user else None,
            "triggered_by_name": user.full_name if user else None,
            "status": analysis.status,
            "error_message": analysis.error_message,
            "started_at": analysis.started_at.isoformat() if analysis.started_at else None,
            "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
            "duration_seconds": round(duration, 1) if duration is not None else None,
        })

    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": (skip + len(items)) < total,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. GET /admin/reports
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/reports",
    summary="[Admin] List all BI reports across all users",
    response_description="Paginated list of all generated reports with verification status",
    status_code=status.HTTP_200_OK,
)
def list_all_reports(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    verification_status: str | None = Query(
        default=None,
        description="Filter: VERIFIED | VERIFIED_WITH_WARNINGS | pending | rejected",
    ),
    has_pdf: bool | None = Query(default=None, description="Filter: only reports with/without a PDF on disk"),
    db: Session = Depends(get_db),
    _admin: User = AdminOnly,
) -> dict:
    """
    Returns every report generated by any user, enriched with dataset name and
    report owner's email.

    **Filters:**
    - `verification_status` — exact match (case-insensitive handled by ILIKE).
    - `has_pdf` — `true` returns only reports whose PDF file exists on disk.

    **Why admin-only?**
    Reports contain confidential financial/operational analysis. Non-admins
    already have scoped access via `GET /reports` (Module 11), which filters
    by their own datasets. The admin view exists for oversight and auditing,
    not for a default user workflow.
    """
    limit = _clamp_limit(limit)

    stmt = (
        select(Report, Analysis, Dataset, User)
        .join(Analysis, Report.analysis_id == Analysis.id)
        .join(Dataset, Analysis.dataset_id == Dataset.id)
        .outerjoin(User, Analysis.user_id == User.id)
        .order_by(Report.created_at.desc())
    )

    if verification_status:
        stmt = stmt.where(Report.verification_status.ilike(verification_status))

    rows, total = _paginate(stmt, db, skip, limit)

    items = []
    for report, analysis, dataset, user in rows:
        pdf_exists = bool(report.pdf_path and os.path.exists(report.pdf_path))

        # Apply has_pdf filter AFTER loading (path existence is not stored in DB)
        if has_pdf is not None and pdf_exists != has_pdf:
            continue

        items.append({
            "id": str(report.id),
            "analysis_id": str(report.analysis_id),
            "dataset_id": str(dataset.id),
            "dataset_name": dataset.name if dataset else "—",
            "triggered_by_email": user.email if user else None,
            "title": report.title,
            "verification_status": report.verification_status,
            "has_pdf": pdf_exists,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        })

    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": (skip + len(items)) < total,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. GET /admin/stats
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/stats",
    summary="[Admin] Platform-wide statistics",
    response_description="Aggregated counts and health metrics for the admin dashboard",
    status_code=status.HTTP_200_OK,
)
def get_platform_stats(
    db: Session = Depends(get_db),
    _admin: User = AdminOnly,
) -> dict:
    """
    Returns a comprehensive snapshot of platform health, designed to populate
    an admin dashboard in a single API call.

    **Metric categories:**
    - 👥 Users      — total, active/inactive, breakdown by role
    - 🗄️ Datasets   — total, created last 30 days
    - 🔬 Analyses   — total, by status, last 30 days, avg duration
    - 📄 Reports    — total, verification status distribution, PDF count
    - ✅ Approvals  — total decisions, approved/rejected, pending
    - 💬 Chat       — total messages sent

    **Performance:**
    Each domain uses one SQL aggregation query (COUNT + CASE expressions)
    rather than multiple queries or Python loops over full result sets.
    Total: ~6 round-trips to the DB regardless of data volume.

    Formula for `avg_analysis_duration_seconds`:
      AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))
      Only for analyses with status = 'completed'.
    """
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    # ── Users ─────────────────────────────────────────────────────────────────
    user_stats = db.execute(
        select(
            func.count(User.id).label("total"),
            func.sum(case((User.is_active == True, 1), else_=0)).label("active"),
            func.sum(case((User.is_active == False, 1), else_=0)).label("inactive"),
            func.sum(case((User.role == "admin", 1), else_=0)).label("admin_count"),
            func.sum(case((User.role == "manager", 1), else_=0)).label("manager_count"),
            func.sum(case((User.role == "analyst", 1), else_=0)).label("analyst_count"),
        )
    ).one()

    # ── Datasets ──────────────────────────────────────────────────────────────
    dataset_stats = db.execute(
        select(
            func.count(Dataset.id).label("total"),
            func.sum(
                case((Dataset.created_at >= thirty_days_ago, 1), else_=0)
            ).label("last_30_days"),
        )
    ).one()

    # ── Analyses ──────────────────────────────────────────────────────────────
    analysis_stats = db.execute(
        select(
            func.count(Analysis.id).label("total"),
            func.sum(case((Analysis.status == "running", 1), else_=0)).label("running"),
            func.sum(case((Analysis.status == "completed", 1), else_=0)).label("completed"),
            func.sum(case((Analysis.status == "failed", 1), else_=0)).label("failed"),
            func.sum(case((Analysis.status == "verification_failed", 1), else_=0)).label("verification_failed"),
            func.sum(
                case((Analysis.started_at >= thirty_days_ago, 1), else_=0)
            ).label("last_30_days"),
        )
    ).one()

    # Average duration — only for completed analyses
    avg_duration_result = db.scalar(
        select(
            func.avg(
                func.extract(
                    "epoch",
                    Analysis.completed_at - Analysis.started_at,
                )
            )
        ).where(
            Analysis.status == "completed",
            Analysis.completed_at.is_not(None),
        )
    )

    # ── Reports ───────────────────────────────────────────────────────────────
    report_stats = db.execute(
        select(
            func.count(Report.id).label("total"),
            func.sum(
                case((Report.verification_status.ilike("VERIFIED"), 1), else_=0)
            ).label("verified"),
            func.sum(
                case((Report.verification_status.ilike("VERIFIED_WITH_WARNINGS"), 1), else_=0)
            ).label("with_warnings"),
            func.sum(
                case((Report.pdf_path.is_not(None), 1), else_=0)
            ).label("pdf_path_set"),
        )
    ).one()

    # ── Approvals ─────────────────────────────────────────────────────────────
    approval_stats = db.execute(
        select(
            func.count(ApprovalHistory.id).label("total"),
            func.sum(case((ApprovalHistory.decision == "approved", 1), else_=0)).label("approved"),
            func.sum(case((ApprovalHistory.decision == "rejected", 1), else_=0)).label("rejected"),
        )
    ).one()

    # Count recommendations still awaiting decision
    pending_recs: int = db.scalar(
        select(func.count(Recommendation.id)).where(
            Recommendation.approval_status == "pending",
            Recommendation.approval_required == True,
        )
    ) or 0

    # ── Chat ──────────────────────────────────────────────────────────────────
    # Import ChatMessage model only here to avoid circular import at module level
    from app.models.chat_message import ChatMessage  # noqa: PLC0415

    total_chat: int = db.scalar(select(func.count(ChatMessage.id))) or 0

    # ── Compose response ──────────────────────────────────────────────────────
    stats = {
        # Users
        "total_users": int(user_stats.total or 0),
        "active_users": int(user_stats.active or 0),
        "inactive_users": int(user_stats.inactive or 0),
        "users_by_role": {
            "admin": int(user_stats.admin_count or 0),
            "manager": int(user_stats.manager_count or 0),
            "analyst": int(user_stats.analyst_count or 0),
        },
        # Datasets
        "total_datasets": int(dataset_stats.total or 0),
        "datasets_last_30_days": int(dataset_stats.last_30_days or 0),
        # Analyses
        "total_analyses": int(analysis_stats.total or 0),
        "analyses_running": int(analysis_stats.running or 0),
        "analyses_completed": int(analysis_stats.completed or 0),
        "analyses_failed": int(analysis_stats.failed or 0),
        "analyses_verification_failed": int(analysis_stats.verification_failed or 0),
        "analyses_last_30_days": int(analysis_stats.last_30_days or 0),
        "avg_analysis_duration_seconds": (
            round(float(avg_duration_result), 1) if avg_duration_result else None
        ),
        # Reports
        "total_reports": int(report_stats.total or 0),
        "reports_verified": int(report_stats.verified or 0),
        "reports_with_warnings": int(report_stats.with_warnings or 0),
        "reports_pdf_generated": int(report_stats.pdf_path_set or 0),
        # Approvals
        "total_approval_decisions": int(approval_stats.total or 0),
        "approvals_approved": int(approval_stats.approved or 0),
        "approvals_rejected": int(approval_stats.rejected or 0),
        "pending_recommendations": pending_recs,
        # Chat
        "total_chat_messages": total_chat,
        # Meta
        "stats_generated_at": datetime.now(timezone.utc).isoformat(),
        "lookback_days_for_recent": 30,
    }

    logger.info("Admin stats computed: %d users, %d analyses", stats["total_users"], stats["total_analyses"])

    return {"success": True, "data": stats}
