"""Shared request dependencies: current user, cookies, rate limiting."""

import time
from collections import defaultdict, deque
from typing import Deque, Optional

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import decode_access_token
from app.core.database import get_db
from app.modules.auth.models import User

ACCESS_COOKIE = "w2l_access"
REFRESH_COOKIE = "w2l_refresh"


# --------------------------------------------------------------- cookies


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """HTTP-only cookies: JavaScript must never be able to read these, which
    rules out localStorage and makes XSS far less useful to an attacker."""
    common = {
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "domain": settings.COOKIE_DOMAIN or None,
        "path": "/",
    }
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        max_age=settings.ACCESS_TOKEN_MINUTES * 60,
        **common,
    )
    # Refresh cookie path scoped to /api/v1/auth/refresh so the browser doesn't send
    # it on every single API call (saves bytes & shrinks attack surface).
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=settings.REFRESH_TOKEN_DAYS * 86400,
        path="/api/v1/auth/refresh",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN or None,
    )


def clear_auth_cookies(response: Response) -> None:
    common = {"domain": settings.COOKIE_DOMAIN or None, "path": "/"}
    response.delete_cookie(ACCESS_COOKIE, **common)
    response.delete_cookie(REFRESH_COOKIE, domain=settings.COOKIE_DOMAIN or None, path="/api/v1/auth/refresh")


# --------------------------------------------------------- authentication


async def current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Cookie first (browsers), Authorization header second (API clients)."""
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:].strip()
    if not token:
        return None
    claims = decode_access_token(token)
    if not claims or claims.get("type") != "access":
        return None
    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError):
        return None
    return await db.get(User, user_id)


async def current_user(user: Optional[User] = Depends(current_user_optional)) -> User:
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# --------------------------------------------------------- rate limiting

# In-process sliding window. Adequate for a single worker; move to Redis
# before running more than one, or the limit multiplies by worker count.
_hits: dict[str, Deque[float]] = defaultdict(deque)


class RateLimiter:
    def __init__(self, times: int, seconds: int, scope: str):
        self.times, self.seconds, self.scope = times, seconds, scope

    async def __call__(self, request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        key = f"{self.scope}:{ip}"
        now = time.monotonic()
        window = _hits[key]
        while window and now - window[0] > self.seconds:
            window.popleft()
        if len(window) >= self.times:
            retry = int(self.seconds - (now - window[0])) + 1
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many attempts. Please wait and try again.",
                headers={"Retry-After": str(retry)},
            )
        window.append(now)


def reset_rate_limits() -> None:
    """Test hook -- the window is process-global."""
    _hits.clear()


async def require_admin(user: User = Depends(current_user)) -> User:
    """Admin-only routes.

    404 rather than 403: a 403 confirms the endpoint exists, which tells a
    probing non-admin exactly what to go after.
    """
    if user.role != "admin":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")
    return user
