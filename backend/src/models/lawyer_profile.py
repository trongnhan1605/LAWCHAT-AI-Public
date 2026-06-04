from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Unicode, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class LawyerProfile(Base):
    __tablename__ = "lawyer_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(Unicode(160), nullable=False)
    slug: Mapped[str] = mapped_column(Unicode(255), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Unicode(180), nullable=False)
    location: Mapped[str] = mapped_column(Unicode(160), nullable=False)
    specialties: Mapped[str] = mapped_column(Unicode(500), nullable=False)
    experience_years: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating: Mapped[str | None] = mapped_column(Unicode(20), nullable=True)
    bio: Mapped[str | None] = mapped_column(Unicode(700), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Unicode(600), nullable=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
