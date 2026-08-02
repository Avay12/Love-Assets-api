"""Backwards-compatibility shim re-exporting dependencies from app.core.deps."""

from app.core.deps import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    RateLimiter,
    clear_auth_cookies,
    current_user,
    current_user_optional,
    require_admin,
    reset_rate_limits,
    set_auth_cookies,
)

__all__ = [
    "ACCESS_COOKIE",
    "REFRESH_COOKIE",
    "RateLimiter",
    "clear_auth_cookies",
    "current_user",
    "current_user_optional",
    "require_admin",
    "reset_rate_limits",
    "set_auth_cookies",
]
