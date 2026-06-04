from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Unicode, UnicodeText, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    chunk_type: Mapped[str | None] = mapped_column(Unicode(32), nullable=True)
    citation_label: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    hierarchy_path: Mapped[str | None] = mapped_column(Unicode(1000), nullable=True)
    article_number: Mapped[str | None] = mapped_column(Unicode(64), nullable=True)
    clause_number: Mapped[str | None] = mapped_column(Unicode(64), nullable=True)
    point_number: Mapped[str | None] = mapped_column(Unicode(64), nullable=True)
    retrieval_text: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    content: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
