from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, Unicode, UnicodeText, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_token: Mapped[str] = mapped_column(Unicode(128), unique=True, nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    session_type: Mapped[str] = mapped_column(Unicode(32), nullable=False, default="public")
    topic_guess: Mapped[str | None] = mapped_column(Unicode(128), nullable=True)
    last_confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    status: Mapped[str] = mapped_column(Unicode(32), nullable=False, default="active")
    escalated_ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(Unicode(32), nullable=False)
    message_type: Mapped[str] = mapped_column(Unicode(32), nullable=False)
    content: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    category_slug: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    warning_text: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    citation_title: Mapped[str | None] = mapped_column(Unicode(500), nullable=True)
    citation_source: Mapped[str | None] = mapped_column(Unicode(1000), nullable=True)
    needs_escalation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
