from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, Unicode, UnicodeText, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class DocumentRelation(Base):
    __tablename__ = "document_relations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    target_document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(Unicode(64), nullable=False, index=True)
    relation_label: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    legal_basis: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
