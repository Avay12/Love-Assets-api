"""Password hashing, token signing and at-rest encryption for OAuth tokens."""

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import settings

# Argon2id with the library defaults, which follow the OWASP recommendation.
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: Optional[str]) -> bool:
    """Constant-ish time check that never raises on a bad hash.

    A dummy verify runs when the account has no password so that an OAuth-only
    or non-existent account takes the same time as a real one -- otherwise the
    response time alone tells an attacker which emails are registered.
    """
    if not password_hash:
        _hasher.hash(password)  # burn equivalent work
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


# ---------------------------------------------------------------- tokens


def create_access_token(user_id: int, minutes: Optional[int] = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=minutes or settings.ACCESS_TOKEN_MINUTES),
        "typ": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    try:
        claims = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    return claims if claims.get("typ") == "access" else None


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """Stored server-side so a database leak does not yield usable tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


def new_family_id() -> str:
    return secrets.token_hex(16)


# ------------------------------------------- single-use, expiring links


def sign_purpose_token(purpose: str, subject: str, minutes: int) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": subject, "purpose": purpose, "iat": now, "exp": now + timedelta(minutes=minutes)},
        settings.SECRET_KEY,
        algorithm="HS256",
    )


def read_purpose_token(purpose: str, token: str) -> Optional[str]:
    try:
        claims = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    return claims.get("sub") if claims.get("purpose") == purpose else None


# ------------------------------------------------- OAuth token storage

def _fernet_key() -> bytes:
    return base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())


def encrypt(value: Optional[str]) -> Optional[str]:
    """Encrypt a provider token before it touches the database."""
    if value is None:
        return None
    from cryptography.fernet import Fernet

    return Fernet(_fernet_key()).encrypt(value.encode()).decode()


def decrypt(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    from cryptography.fernet import Fernet, InvalidToken

    try:
        return Fernet(_fernet_key()).decrypt(value.encode()).decode()
    except InvalidToken:
        return None


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)
