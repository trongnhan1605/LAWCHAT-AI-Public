from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Unicode, UnicodeText, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class LegalConcept(Base):
    __tablename__ = "legal_concepts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(Unicode(128), nullable=False, unique=True, index=True)
    canonical_name: Mapped[str] = mapped_column(Unicode(255), nullable=False, index=True)
    concept_type: Mapped[str] = mapped_column(Unicode(64), nullable=False, index=True)
    legal_domain: Mapped[str | None] = mapped_column(Unicode(128), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    is_seed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)