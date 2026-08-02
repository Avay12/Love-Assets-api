from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Text, DateTime, JSON, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

JsonCol = JSON().with_variant(JSONB(), "postgresql")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Letter(Base):
    __tablename__ = "letters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    
    type: Mapped[str] = mapped_column(String(32), default="love", nullable=False)
    template_id: Mapped[str] = mapped_column(String(64), default="mailbox", nullable=False)
    
    from_name: Mapped[str] = mapped_column(String(128), nullable=False)
    to_name: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    photos: Mapped[Optional[List[str]]] = mapped_column(JsonCol, default=list)
    details: Mapped[Optional[dict]] = mapped_column(JsonCol, default=dict)
    
    song_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    song_title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    song_artist: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    song_preview_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    delivery_method: Mapped[str] = mapped_column(String(32), default="link", nullable=False)
    delivery_contact: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
