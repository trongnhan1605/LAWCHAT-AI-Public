from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, Unicode, UnicodeText, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ValidationRun(Base):
    __tablename__ = "validation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("legal_cases.id"), nullable=True, index=True)
    planner_run_id: Mapped[int | None] = mapped_column(ForeignKey("planner_runs.id"), nullable=True, index=True)
    reasoning_run_id: Mapped[int | None] = mapped_column(ForeignKey("reasoning_runs.id"), nullable=True, index=True)
    response_text: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    validation_status: Mapped[str] = mapped_column(Unicode(32), nullable=False, default="pending", index=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    escalation_recommended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    findings_json: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    error_message: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
