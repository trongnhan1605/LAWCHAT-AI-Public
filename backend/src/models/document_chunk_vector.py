from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Unicode, UnicodeText, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class DocumentChunkVector(Base):
    __tablename__ = "document_chunk_vectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chunk_id: Mapped[int] = mapped_column(ForeignKey("document_chunks.id"), nullable=False, unique=True, index=True)
    provider: Mapped[str] = mapped_column(Unicode(32), nullable=False)
    embedding_model: Mapped[str] = mapped_column(Unicode(128), nullable=False)
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding_status: Mapped[str] = mapped_column(Unicode(32), nullable=False, default="pending")
    embedding_json: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    error_message: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)