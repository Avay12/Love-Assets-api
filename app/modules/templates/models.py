from typing import Optional
from sqlalchemy import String, Text, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    subtitle: Mapped[str] = mapped_column(String(256), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(32), default="love", nullable=False)
    experience: Mapped[str] = mapped_column(String(32), default="photo", nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    is_birthday_exclusive: Mapped[bool] = mapped_column(Boolean, default=False)
