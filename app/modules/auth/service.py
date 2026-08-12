"""Registration, sign-in, session rotation and OAuth account linking."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import (
    create_access_token,
    encrypt,
    hash_password,
    hash_refresh_token,
    needs_rehash,
    new_family_id,
    new_refresh_token,
    verify_password,
)
from app.modules.auth.models import OAuthIdentity, Session, User

INVALID_CREDENTIALS = "Invalid email or password."


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AuthService:
    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.strip())
        found = await db.scalar(stmt)
        if found or settings.is_postgres:
            return found
        rows = (await db.execute(select(User))).scalars().all()
        return next((u for u in rows if u.email.lower() == email.strip().lower()), None)

    @staticmethod
    async def register(db: AsyncSession, name: str, email: str, password: str) -> User:
        if await AuthService.get_by_email(db, email):
            raise HTTPException(status.HTTP_409_CONFLICT, "An account with that email already exists.")

        # Role is never taken from the request. scripts/make_admin.py is the
        # only way to promote an account.
        user = User(
            name=name.strip(),
            email=email.strip().lower(),
            password_hash=hash_password(password),
            role="user",
            timezone="UTC",
            email_verified_at=_now(),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate(db: AsyncSession, email: str, password: str) -> User:
        user = await AuthService.get_by_email(db, email)
        if not verify_password(password, user.password_hash if user else None) or user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_CREDENTIALS)

        if user.password_hash and needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
            await db.commit()
        return user

    @staticmethod
    async def issue_session(
        db: AsyncSession, user: User, request: Optional[Request] = None, family_id: Optional[str] = None
    ) -> Tuple[str, str]:
        refresh = new_refresh_token()
        db.add(
            Session(
                user_id=user.id,
                refresh_token_hash=hash_refresh_token(refresh),
                family_id=family_id or new_family_id(),
                user_agent=(request.headers.get("user-agent") if request else None or "")[:256] or None,
                ip=(request.client.host if request and request.client else None),
                expires_at=_now() + timedelta(days=settings.REFRESH_TOKEN_DAYS),
            )
        )
        await db.commit()
        return create_access_token(user.id), refresh

    @staticmethod
    async def rotate(db: AsyncSession, refresh_token: str, request: Optional[Request] = None) -> Tuple[str, str, User]:
        token_hash = hash_refresh_token(refresh_token)
        row = await db.scalar(select(Session).where(Session.refresh_token_hash == token_hash))

        if row is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session.")

        if row.revoked_at is not None:
            await db.execute(
                update(Session)
                .where(Session.family_id == row.family_id, Session.revoked_at.is_(None))
                .values(revoked_at=_now())
            )
            await db.commit()
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session replay detected. Please sign in again.")

        expires = row.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < _now():
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired.")

        user = await db.get(User, row.user_id)
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session.")

        row.revoked_at = _now()
        await db.flush()
        access, new_refresh = await AuthService.issue_session(db, user, request, family_id=row.family_id)
        return access, new_refresh, user

    @staticmethod
    async def revoke(db: AsyncSession, refresh_token: str) -> None:
        row = await db.scalar(select(Session).where(Session.refresh_token_hash == hash_refresh_token(refresh_token)))
        if row and row.revoked_at is None:
            row.revoked_at = _now()
            await db.commit()

    @staticmethod
    async def revoke_all(db: AsyncSession, user_id: int) -> None:
        await db.execute(
            update(Session).where(Session.user_id == user_id, Session.revoked_at.is_(None)).values(revoked_at=_now())
        )
        await db.commit()

    @staticmethod
    async def link_or_create(
        db: AsyncSession,
        provider: str,
        provider_account_id: str,
        email: Optional[str],
        name: Optional[str],
        avatar_url: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ) -> User:
        identity = await db.scalar(
            select(OAuthIdentity).where(
                OAuthIdentity.provider == provider,
                OAuthIdentity.provider_account_id == provider_account_id,
            )
        )
        if identity:
            user = await db.get(User, identity.user_id)
            if user:
                identity.access_token = encrypt(access_token)
                identity.refresh_token = encrypt(refresh_token)
                await db.commit()
                return user

        if not email:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"{provider.title()} did not share an email address, so the account cannot be linked.",
            )

        user = await AuthService.get_by_email(db, email)
        if user is None:
            user = User(
                name=(name or email.split("@")[0]).strip(),
                email=email.strip().lower(),
                password_hash=None,
                avatar_url=avatar_url,
                email_verified_at=_now(),
            )
            db.add(user)
            await db.flush()
        elif user.avatar_url is None and avatar_url:
            user.avatar_url = avatar_url

        db.add(
            OAuthIdentity(
                user_id=user.id,
                provider=provider,
                provider_account_id=provider_account_id,
                access_token=encrypt(access_token),
                refresh_token=encrypt(refresh_token),
            )
        )
        await db.commit()
        await db.refresh(user)
        return user
