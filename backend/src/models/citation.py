from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Unicode, UnicodeText, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    planner_run_id: Mapped[int | None] = mapped_column(ForeignKey("planner_runs.id"), nullable=True, index=True)
    reasoning_run_id: Mapped[int | None] = mapped_column(ForeignKey("reasoning_runs.id"), nullable=True, index=True)
    validation_run_id: Mapped[int | None] = mapped_column(ForeignKey("validation_runs.id"), nullable=True, index=True)
    chat_message_id: Mapped[int | None] = mapped_column(ForeignKey("chat_messages.id"), nullable=True, index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True, index=True)
    chunk_id: Mapped[int | None] = mapped_column(ForeignKey("document_chunks.id"), nullable=True, index=True)
    citation_type: Mapped[str] = mapped_column(Unicode(64), nullable=False, default="legal_basis", index=True)
    document_title: Mapped[str | None] = mapped_column(Unicode(500), nullable=True)
    citation_label: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    hierarchy_path: Mapped[str | None] = mapped_column(Unicode(1000), nullable=True)
    source_reference: Mapped[str | None] = mapped_column(Unicode(500), nullable=True)
    excerpt: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
