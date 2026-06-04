from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, Unicode, UnicodeText, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False, index=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("legal_cases.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(Unicode(500), nullable=False)
    topic: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    escalation_reason: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    status: Mapped[str] = mapped_column(Unicode(32), nullable=False, default="new")
    priority: Mapped[str] = mapped_column(Unicode(16), nullable=False, default="normal")
    consultant_note: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
