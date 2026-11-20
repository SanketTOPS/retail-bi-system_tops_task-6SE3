"""
app/models/chat_message.py
───────────────────────────
Stores AI chat conversation history between a user and the system.
Used by the AI Chat Interface page on the React frontend.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ChatMessage(Base):
    """
    One message in the AI chat conversation.

    role: 'user' (human input) | 'assistant' (AI response)
    """

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── FK ────────────────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Message ───────────────────────────────────────────────────────────────
    role: Mapped[str] = mapped_column(
        Enum("user", "assistant", name="chat_role_enum"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Context ───────────────────────────────────────────────────────────────
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional link to the analysis context used for this chat turn",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="chat_messages")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<ChatMessage role={self.role} user={self.user_id}>"
