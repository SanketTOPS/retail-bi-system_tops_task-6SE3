"""
app/schemas/dataset.py
───────────────────────
Pydantic v2 schemas for Dataset upload, processing, preview, and details.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CleaningSheetStats(BaseModel):
    """Statistics on cleaning for a single dataset sheet."""
    rows_initial: int = 0
    rows_final: int = 0
    duplicates_removed: int = 0
    nulls_handled: int = 0
    date_filtered_rows: int = 0
    invalid_values_dropped: int = 0
    orphan_rows_dropped: int = 0
    details: list[str] = Field(default_factory=list)


class CleaningSummary(BaseModel):
    """Overall cleaning summary across all sheets."""
    dataset_period: str = "2026-05-01 to 2026-10-31"
    sheets: dict[str, CleaningSheetStats] = Field(default_factory=dict)
    total_rows_imported: int = 0


class DatasetResponse(BaseModel):
    """Detailed response for a single dataset record."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    original_filename: str
    stored_filename: str
    file_size_bytes: int | None = None
    status: str
    row_counts: dict[str, int] | None = None
    cleaning_summary: dict[str, Any] | None = None
    error_message: str | None = None
    uploaded_at: datetime
    processed_at: datetime | None = None


class DatasetListItem(BaseModel):
    """Concise representation of a dataset for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    file_size_bytes: int | None = None
    status: str
    total_rows: int = 0
    row_counts: dict[str, int] | None = None
    uploaded_at: datetime
    processed_at: datetime | None = None


class DatasetPreviewResponse(BaseModel):
    """Preview of records per table/sheet (typically first 5-10 rows)."""
    dataset_id: uuid.UUID
    filename: str
    previews: dict[str, list[dict[str, Any]]]


class DatasetUploadResponse(BaseModel):
    """Response returned immediately after file upload & processing."""
    success: bool = True
    message: str
    dataset: DatasetResponse
