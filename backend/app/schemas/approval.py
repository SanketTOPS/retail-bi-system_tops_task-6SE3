"""
app/schemas/approval.py
────────────────────────
Pydantic v2 schemas for Human-in-the-Loop approval workflows.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DecisionRequest(BaseModel):
    action: Literal["approve", "reject"] = Field(
        ...,
        examples=["approve"],
        description="Managerial decision: 'approve' or 'reject'",
    )
    comment: str | None = Field(
        None,
        max_length=2000,
        examples=["Approved: 15% marketing budget expansion authorized for Q3."],
        description="Optional managerial rationale or operational instructions",
    )


class DecisionResponse(BaseModel):
    success: bool = True
    recommendation_id: uuid.UUID
    action: str
    approval_status: str
    comment: str | None = None
    execution_status: str = "approved_for_execution"
    execution_log: str | None = None
    decided_at: datetime


class PendingApprovalItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recommendation_id: uuid.UUID
    analysis_id: uuid.UUID
    title: str
    description: str
    category: str
    expected_impact: str | None = None
    priority: int
    approval_status: str
    report_verification_status: str
    created_at: datetime


class ApprovalHistoryItem(BaseModel):
    id: uuid.UUID
    recommendation_id: uuid.UUID
    recommendation_title: str
    category: str
    approver_id: uuid.UUID | None = None
    approver_name: str | None = None
    approver_role: str | None = None
    decision: str
    comment: str | None = None
    decided_at: datetime
