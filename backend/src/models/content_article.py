from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Unicode, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ContentArticle(Base):
    __tablename__ = "content_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    slug: Mapped[str] = mapped_column(Unicode(255), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(Unicode(120), nullable=False)
    excerpt: Mapped[str] = mapped_column(Unicode(600), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Unicode(600), nullable=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
