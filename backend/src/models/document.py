from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, Unicode, UnicodeText, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(Unicode(500), nullable=False)
    file_name: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    source_type: Mapped[str] = mapped_column(Unicode(16), nullable=False)
    legal_domain: Mapped[str] = mapped_column(Unicode(128), nullable=False, default="labor_law")
    authority_level: Mapped[str | None] = mapped_column(Unicode(64), nullable=True)
    issuing_authority: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    document_code: Mapped[str | None] = mapped_column(Unicode(128), nullable=True)
    document_type: Mapped[str | None] = mapped_column(Unicode(64), nullable=True)
    normative_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    signed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_reference: Mapped[str | None] = mapped_column(Unicode(500), nullable=True)
    storage_path: Mapped[str] = mapped_column(Unicode(1000), nullable=False)
    summary: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    legal_status: Mapped[str | None] = mapped_column(Unicode(32), nullable=True, default="active")
    metadata_review_status: Mapped[str] = mapped_column(Unicode(32), nullable=False, default="pending_review")
    metadata_review_notes: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    metadata_last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_sha256: Mapped[str | None] = mapped_column(Unicode(64), nullable=True, index=True)
    source_identity: Mapped[str | None] = mapped_column(Unicode(512), nullable=True, index=True)
    ingestion_quality_status: Mapped[str] = mapped_column(Unicode(32), nullable=False, default="pending")
    ingestion_quality_notes: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    retrieval_visibility: Mapped[str] = mapped_column(Unicode(32), nullable=False, default="indexed_unreviewed")
    ocr_quality_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    ocr_quality_label: Mapped[str | None] = mapped_column(Unicode(32), nullable=True)
    relation_sync_status: Mapped[str] = mapped_column(Unicode(32), nullable=False, default="pending")
    relation_sync_details: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    is_seed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
