from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, Unicode, UnicodeText, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class AIRequestUsage(Base):
    __tablename__ = "ai_request_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_type: Mapped[str] = mapped_column(Unicode(32), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(Unicode(64), nullable=False)
    provider: Mapped[str] = mapped_column(Unicode(32), nullable=False)
    model: Mapped[str] = mapped_column(Unicode(128), nullable=False)
    request_identifier: Mapped[str | None] = mapped_column(Unicode(128), nullable=True, index=True)
    document_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    document_title_snapshot: Mapped[str | None] = mapped_column(Unicode(500), nullable=True)
    file_name_snapshot: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    storage_path_snapshot: Mapped[str | None] = mapped_column(Unicode(1000), nullable=True, index=True)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cached_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    web_search_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    status: Mapped[str] = mapped_column(Unicode(32), nullable=False, default="success")
    error_message: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    raw_usage_json: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)