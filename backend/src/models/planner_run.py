from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Unicode, UnicodeText, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class PlannerRun(Base):
    __tablename__ = "planner_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("legal_cases.id"), nullable=True, index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("chat_sessions.id"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    query_text: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    detected_intent: Mapped[str | None] = mapped_column(Unicode(64), nullable=True, index=True)
    detected_domain: Mapped[str | None] = mapped_column(Unicode(128), nullable=True, index=True)
    complexity_level: Mapped[str | None] = mapped_column(Unicode(32), nullable=True, index=True)
    status: Mapped[str] = mapped_column(Unicode(32), nullable=False, default="pending", index=True)
    plan_json: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    context_json: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    result_json: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    error_message: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
