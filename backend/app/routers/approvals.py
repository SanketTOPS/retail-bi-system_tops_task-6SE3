"""
app/routers/approvals.py
─────────────────────────
Router for Human-in-the-Loop (HITL) approval workflows.

Security:
  Strictly restricted to 'manager' and 'admin' roles via require_roles("manager", "admin").
  Users with the 'analyst' role receive HTTP 403 Forbidden.

Rules Enforced:
  1. Only recommendations from VERIFIED reports can be approved/rejected.
  2. A decision can only be made once (idempotent / non-reversible).
  3. Decisions write an immutable audit trail entry to approval_history.
  4. No consequential business action executes automatically without authorized managerial consent.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Sequence

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.main import AppException
from app.models.analysis import Analysis
from app.models.approval import ApprovalHistory
from app.models.recommendation import Recommendation
from app.models.report import Report
from app.models.user import User
from app.schemas.approval import (
    ApprovalHistoryItem,
    DecisionRequest,
    DecisionResponse,
    PendingApprovalItem,
)
from app.utils.deps import require_roles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/approvals", tags=["Human-in-the-Loop Approvals"])

# Allowed verification statuses eligible for human decision
VALID_REPORT_STATUSES = {"VERIFIED", "VERIFIED_WITH_WARNINGS", "approved"}


@router.get(
    "/pending",
    response_model=list[PendingApprovalItem],
    summary="List Pending Recommendations for Approval",
    description=(
        "Retrieves all consequential recommendations awaiting human management decision. "
        "Restricted to managers and administrators. "
        "Enforces rule: ONLY recommendations from VERIFIED reports are returned."
    ),
    responses={
        200: {"description": "List of pending recommendations"},
        403: {"description": "Forbidden: Requires manager or admin role"},
    },
)
def get_pending_approvals(
    current_user: User = Depends(require_roles("manager", "admin")),
    db: Session = Depends(get_db),
) -> list[PendingApprovalItem]:
    """Fetch pending recommendations from verified reports."""
    stmt = (
        select(Recommendation, Report.verification_status)
        .join(Analysis, Recommendation.analysis_id == Analysis.id)
        .join(Report, Analysis.id == Report.analysis_id)
        .where(Recommendation.approval_required == True)  # noqa: E712
        .where(Recommendation.approval_status == "pending")
        .where(Report.verification_status.in_(VALID_REPORT_STATUSES))
        .order_by(Recommendation.priority.asc(), Recommendation.created_at.desc())
    )
    rows = db.execute(stmt).all()

    items: list[PendingApprovalItem] = []
    for rec, ver_status in rows:
        items.append(
            PendingApprovalItem(
                recommendation_id=rec.id,
                analysis_id=rec.analysis_id,
                title=rec.title,
                description=rec.description,
                category=rec.category,
                expected_impact=rec.expected_impact,
                priority=rec.priority,
                approval_status=rec.approval_status,
                report_verification_status=ver_status,
                created_at=rec.created_at,
            )
        )
    return items


@router.post(
    "/{recommendation_id}/decision",
    response_model=DecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Record Managerial Decision (Approve / Reject)",
    description=(
        "Submits an authorized management decision on a consequential recommendation. "
        "Requires 'manager' or 'admin' role (analyst receives 403 Forbidden). "
        "Enforces that the parent report is verified, and that a decision can only be recorded once."
    ),
    responses={
        200: {"description": "Decision successfully recorded"},
        400: {"description": "Cannot decide on unverified report"},
        403: {"description": "Forbidden: Requires manager or admin role"},
        404: {"description": "Recommendation not found"},
        409: {"description": "Decision already recorded for this recommendation"},
    },
)
def record_decision(
    recommendation_id: uuid.UUID,
    payload: DecisionRequest,
    current_user: User = Depends(require_roles("manager", "admin")),
    db: Session = Depends(get_db),
) -> DecisionResponse:
    """Record manager decision and simulate operational execution."""
    # 1. Fetch recommendation
    rec = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not rec:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation '{recommendation_id}' not found.",
            code="RECOMMENDATION_NOT_FOUND",
        )

    # 2. Check parent report verification status
    report = db.query(Report).filter(Report.analysis_id == rec.analysis_id).first()
    if not report or report.verification_status not in VALID_REPORT_STATUSES:
        ver_status = report.verification_status if report else "NONE"
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot record decision on recommendation '{rec.title}'. "
                f"The parent report verification status is '{ver_status}'. "
                "Managerial approvals are strictly prohibited on unverified or rejected reports."
            ),
            code="REPORT_NOT_VERIFIED",
        )

    # 3. Guard against duplicate decision (one decision per recommendation)
    if rec.approval_status != "pending":
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Recommendation '{rec.title}' has already been decided "
                f"(Current status: '{rec.approval_status}'). Decisions are final and non-reversible."
            ),
            code="DECISION_ALREADY_RECORDED",
        )

    # 4. Update Recommendation status
    now = datetime.now(timezone.utc)
    new_status = "approved" if payload.action == "approve" else "rejected"
    rec.approval_status = new_status

    # 5. Insert immutable audit record into ApprovalHistory
    history_entry = ApprovalHistory(
        recommendation_id=rec.id,
        approver_id=current_user.id,
        decision=payload.action,
        comment=payload.comment,
        decided_at=now,
    )
    db.add(history_entry)

    # 6. Simulate operational execution
    execution_status = "approved_for_execution" if payload.action == "approve" else "rejected_by_management"
    if payload.action == "approve":
        simulated_log = (
            f"[EXECUTION LOG] Consequential action '{rec.title}' approved by {current_user.full_name} "
            f"({current_user.role}). Dispatched to retail ERP & inventory dispatch queue."
        )
    else:
        simulated_log = (
            f"[EXECUTION LOG] Action '{rec.title}' rejected by {current_user.full_name} "
            f"({current_user.role}). Shelved in audit history; no operational changes dispatched."
        )

    db.commit()
    logger.info(
        "Manager %s (%s) recorded %s on recommendation %s: %s",
        current_user.email,
        current_user.role,
        payload.action.upper(),
        rec.id,
        rec.title,
    )

    return DecisionResponse(
        success=True,
        recommendation_id=rec.id,
        action=payload.action,
        approval_status=rec.approval_status,
        comment=payload.comment,
        execution_status=execution_status,
        execution_log=simulated_log,
        decided_at=now,
    )


@router.get(
    "/history",
    response_model=list[ApprovalHistoryItem],
    summary="Get Approval Decision Audit History",
    description="Returns chronological audit trail of all managerial approval decisions made across the organization.",
    responses={
        200: {"description": "Chronological audit trail of decisions"},
        403: {"description": "Forbidden: Requires manager or admin role"},
    },
)
def get_approval_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_roles("manager", "admin")),
    db: Session = Depends(get_db),
) -> list[ApprovalHistoryItem]:
    """Retrieve full audit history of decisions."""
    stmt = (
        select(ApprovalHistory, Recommendation.title, Recommendation.category, User.full_name, User.role)
        .join(Recommendation, ApprovalHistory.recommendation_id == Recommendation.id)
        .outerjoin(User, ApprovalHistory.approver_id == User.id)
        .order_by(ApprovalHistory.decided_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = db.execute(stmt).all()

    history: list[ApprovalHistoryItem] = []
    for h, rec_title, rec_category, user_name, user_role in rows:
        history.append(
            ApprovalHistoryItem(
                id=h.id,
                recommendation_id=h.recommendation_id,
                recommendation_title=rec_title,
                category=rec_category,
                approver_id=h.approver_id,
                approver_name=user_name,
                approver_role=user_role,
                decision=h.decision,
                comment=h.comment,
                decided_at=h.decided_at,
            )
        )
    return history
