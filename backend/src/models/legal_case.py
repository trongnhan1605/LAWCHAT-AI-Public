from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Unicode, UnicodeText, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class LegalCase(Base):
    __tablename__ = "legal_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("chat_sessions.id"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    legal_domain: Mapped[str] = mapped_column(Unicode(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(Unicode(32), nullable=False, default="intake", index=True)
    risk_level: Mapped[str] = mapped_column(Unicode(32), nullable=False, default="low", index=True)
    summary: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    desired_outcome: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    intake_snapshot_json: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    structured_facts_json: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
