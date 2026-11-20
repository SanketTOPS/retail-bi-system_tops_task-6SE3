"""
app/schemas/report.py
─────────────────────
Pydantic response schemas for the Reports router (Module 11).

These are thin wrappers used in type hints / OpenAPI docs.
The actual payload is returned as plain dicts from the router
(FastAPI serialises them automatically).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ReportListItem(BaseModel):
    """Summary row returned by GET /reports."""

    report_id: uuid.UUID
    analysis_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_name: str
    title: str
    verification_status: str
    has_pdf: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReportDetailResponse(BaseModel):
    """Full report content returned by GET /reports/{analysis_id}."""

    report_id: uuid.UUID
    analysis_id: uuid.UUID
    dataset_id: uuid.UUID
    title: str
    executive_summary: str | None = None
    verification_status: str
    verification_notes: str | None = None
    content: dict[str, Any] = {}
    has_pdf: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
