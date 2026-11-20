"""
app/schemas/chat.py
────────────────────
Pydantic v2 schemas for Business Intelligence AI Chat conversations.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatMessageRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=2,
        max_length=2000,
        examples=["What were our top 3 revenue-generating product categories in Q3?"],
        description="Business or retail analytical inquiry (2 to 2000 characters)",
    )
    analysis_id: uuid.UUID | None = Field(
        None,
        description="Optional analysis ID to anchor conversation context to a specific dataset/report run",
    )


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    analysis_id: uuid.UUID | None = None
    created_at: datetime


class ChatTurnResponse(BaseModel):
    success: bool = True
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    dataset_id: uuid.UUID | None = None


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageResponse] = Field(default_factory=list)
    total_count: int = 0
