from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Case-insensitive email on Postgres so Alex@x.com and alex@x.com are one
# account; plain string on SQLite, where the test suite lowercases instead.
EmailCol = String(320).with_variant(CITEXT(), "postgresql")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(EmailCol, unique=True, nullable=False, index=True)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Null for accounts that only ever signed in through an OAuth provider.
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    identities: Mapped[List["OAuthIdentity"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    sessions: Mapped[List["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )


class OAuthIdentity(Base):
    """One row per (provider, account) pair linked to a user.

    Keeping identities in their own table is what allows a Google sign-in to
    attach to an existing password account instead of creating a duplicate.
    """

    __tablename__ = "oauth_identities"
    __table_args__ = (UniqueConstraint("provider", "provider_account_id", name="uq_oauth_provider_account"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_account_id: Mapped[str] = mapped_column(String(191), nullable=False)

    # Encrypted at rest; see app.core.crypto.
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="identities")


class Session(Base):
    """A refresh-token family.

    Each refresh rotates the token and keeps family_id. If a token that has
    already been rotated is presented again, the whole family is revoked --
    that is the stolen-token signal.
    """

    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_user_active", "user_id", "revoked_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # sha256 of the refresh token; the raw value only ever lives in the cookie.
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    family_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    user_agent: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="sessions")
