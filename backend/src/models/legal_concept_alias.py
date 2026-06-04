from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Unicode, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class LegalConceptAlias(Base):
    __tablename__ = "legal_concept_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("legal_concepts.id"), nullable=False, index=True)
    alias_text: Mapped[str] = mapped_column(Unicode(255), nullable=False, index=True)
    alias_type: Mapped[str] = mapped_column(Unicode(32), nullable=False, default="synonym")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)