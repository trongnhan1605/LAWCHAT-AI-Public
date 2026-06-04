from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, Unicode, UnicodeText, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class CaseFact(Base):
    __tablename__ = "case_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("legal_cases.id"), nullable=False, index=True)
    source_message_id: Mapped[int | None] = mapped_column(ForeignKey("chat_messages.id"), nullable=True, index=True)
    fact_type: Mapped[str] = mapped_column(Unicode(64), nullable=False, index=True)
    fact_key: Mapped[str] = mapped_column(Unicode(128), nullable=False, index=True)
    fact_value: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    happened_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_disputed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
