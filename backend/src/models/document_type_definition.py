from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Unicode, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class DocumentTypeDefinition(Base):
    __tablename__ = "document_type_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(Unicode(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(Unicode(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Unicode(500), nullable=True)
    normative_level: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)