from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Text, DateTime, JSON, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# JSONB on Postgres (indexable, binary, no key-order churn); plain JSON on
# SQLite, which the test suite uses.
JsonCol = JSON().with_variant(JSONB(), "postgresql")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Letter(Base):
    __tablename__ = "letters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    
    # Configuration
    type: Mapped[str] = mapped_column(String(32), default="love", nullable=False)
    template_id: Mapped[str] = mapped_column(String(64), default="mailbox", nullable=False)
    
    # Core Content
    from_name: Mapped[str] = mapped_column(String(128), nullable=False)
    to_name: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Media & Assets
    photos: Mapped[Optional[List[str]]] = mapped_column(JsonCol, default=list)

    # Type-specific payload (age, event date/venue, gift accounts, ...).
    # Kept as JSON so each letter type can carry its own shape without a table
    # per type; the per-type Pydantic schemas are what actually validate it.
    details: Mapped[Optional[dict]] = mapped_column(JsonCol, default=dict)
    
    # Music Track
    song_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    song_title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    song_artist: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    song_preview_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    # Delivery Info
    delivery_method: Mapped[str] = mapped_column(String(32), default="link", nullable=False)
    delivery_contact: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
