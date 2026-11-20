"""
app/routers/chat.py
────────────────────
Router for the Business Intelligence AI Chat Interface.

Endpoints:
  POST   /api/v1/chat          — Ask business question to grounded CrewAI Q&A Agent
  GET    /api/v1/chat/history  — Retrieve paginated conversation history
  DELETE /api/v1/chat/history  — Clear conversation history for authenticated user
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.chat_message import ChatMessage
from app.models.user import User
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatTurnResponse,
)
from app.services import chat_service
from app.utils.deps import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Business AI Chat"])


@router.post(
    "",
    response_model=ChatTurnResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask Business AI Question",
    description=(
        "Interacts with an intelligent, tool-grounded Business Intelligence Advisor. "
        "Anchors answers to the specified analysis or latest verified report. "
        "Strictly redirects non-business questions and answers 'Data not available' instead of guessing."
    ),
    responses={
        200: {"description": "Grounded answer returned with chat turn records"},
        400: {"description": "Invalid question input"},
        404: {"description": "Referenced analysis not found"},
    },
)
def send_chat_message(
    payload: ChatMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ChatTurnResponse:
    """Send natural language inquiry to grounded AI advisor."""
    user_msg, assistant_msg, dataset_id = chat_service.process_chat_message(
        db=db,
        user=current_user,
        message=payload.message,
        analysis_id=payload.analysis_id,
    )

    return ChatTurnResponse(
        success=True,
        user_message=ChatMessageResponse.model_validate(user_msg),
        assistant_message=ChatMessageResponse.model_validate(assistant_msg),
        dataset_id=dataset_id,
    )


@router.get(
    "/history",
    response_model=ChatHistoryResponse,
    summary="Get Chat Conversation History",
    description="Returns chronological conversation history for the current user.",
)
def get_chat_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ChatHistoryResponse:
    """Fetch paginated message logs."""
    messages, total = chat_service.get_chat_history(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return ChatHistoryResponse(
        messages=[ChatMessageResponse.model_validate(m) for m in messages],
        total_count=total,
    )


@router.delete(
    "/history",
    status_code=status.HTTP_200_OK,
    summary="Clear Chat Conversation History",
    description="Clears all conversation messages for the current user.",
)
def clear_chat_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Delete all user chat messages."""
    stmt = delete(ChatMessage).where(ChatMessage.user_id == current_user.id)
    db.execute(stmt)
    db.commit()
    return {"success": True, "message": "Conversation history cleared successfully."}
