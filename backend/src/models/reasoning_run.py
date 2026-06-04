from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Unicode, UnicodeText, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ReasoningRun(Base):
    __tablename__ = "reasoning_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("legal_cases.id"), nullable=True, index=True)
    planner_run_id: Mapped[int | None] = mapped_column(ForeignKey("planner_runs.id"), nullable=True, index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("chat_sessions.id"), nullable=True, index=True)
    issue_summary: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    reasoning_graph_json: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    evidence_json: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    conclusion_json: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    status: Mapped[str] = mapped_column(Unicode(32), nullable=False, default="pending", index=True)
    error_message: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
