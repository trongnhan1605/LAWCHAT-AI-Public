from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Unicode, UnicodeText, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class LegalProvision(Base):
    __tablename__ = "legal_provisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    parent_provision_id: Mapped[int | None] = mapped_column(ForeignKey("legal_provisions.id"), nullable=True, index=True)
    provision_level: Mapped[str] = mapped_column(Unicode(16), nullable=False, index=True)
    article_number: Mapped[str | None] = mapped_column(Unicode(32), nullable=True, index=True)
    clause_number: Mapped[str | None] = mapped_column(Unicode(32), nullable=True)
    point_code: Mapped[str | None] = mapped_column(Unicode(32), nullable=True)
    heading: Mapped[str | None] = mapped_column(Unicode(500), nullable=True)
    content: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    citation_label: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    sort_key: Mapped[str] = mapped_column(Unicode(128), nullable=False, index=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    legal_status: Mapped[str | None] = mapped_column(Unicode(32), nullable=True, default="active")
    metadata_json: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
