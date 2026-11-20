"""
app/schemas/analysis.py
────────────────────────
Pydantic v2 schemas for Analysis run initiation, status tracking,
real-time agent logging, and report retrieval.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AnalysisRunRequest(BaseModel):
    dataset_id: uuid.UUID = Field(..., description="Target dataset UUID to analyze")
    user_question: str | None = Field(
        None,
        max_length=1000,
        examples=["Why did gross margin drop in August?"],
        description="Optional strategic inquiry for agents to specifically investigate",
    )


class AnalysisRunResponse(BaseModel):
    success: bool = True
    analysis_id: uuid.UUID
    dataset_id: uuid.UUID
    status: str = "running"
    message: str = "Multi-agent intelligence analysis initiated in the background."


class AgentStatusItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_name: str
    sequence_order: int
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None


class AnalysisStatusResponse(BaseModel):
    analysis_id: uuid.UUID
    dataset_id: uuid.UUID
    status: str
    current_agent: str | None = None
    progress_pct: int = 0
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    agents: list[AgentStatusItem] = Field(default_factory=list)


class AgentLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_name: str
    sequence_order: int
    status: str
    input_summary: str | None = None
    raw_output: str | None = None
    error_detail: str | None = None
    duration_seconds: float | None = None
    started_at: datetime
    completed_at: datetime | None = None


class AnalysisLogsResponse(BaseModel):
    analysis_id: uuid.UUID
    logs: list[AgentLogItem] = Field(default_factory=list)


class AnalysisReportResponse(BaseModel):
    report_id: uuid.UUID
    analysis_id: uuid.UUID
    dataset_id: uuid.UUID
    title: str
    executive_summary: str | None = None
    content_json: dict[str, Any] | None = None
    verification_status: str
    verification_notes: dict[str, Any] | str | None = None
    pdf_path: str | None = None
    created_at: datetime
    recommendations: list[dict[str, Any]] = Field(default_factory=list)


class AnalysisHistoryItem(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    original_filename: str = "Dataset"
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    has_report: bool = False
    verification_status: str | None = None
