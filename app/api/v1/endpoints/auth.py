"""Authentication: email/password, sessions, and OAuth (Google, GitHub)."""

import base64
import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    RateLimiter,
    clear_auth_cookies,
    current_user,
    set_auth_cookies,
)
from app.core.config import settings
from app.core.crypto import hash_password, read_purpose_token, sign_purpose_token
from app.core.database import get_db
from app.db.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter()

PROVIDERS = {
    "google": {
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "userinfo": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile",
    },
    "github": {
        "authorize": "https://github.com/login/oauth/authorize",
        "token": "https://github.com/login/oauth/access_token",
        "userinfo": "https://api.github.com/user",
        "scope": "read:user user:email",
    },
}

# state -> (code_verifier, return_to). Single-process, like the rate limiter;
# move to Redis alongside it. Entries are consumed on callback.
_pending: dict[str, tuple[str, str]] = {}


def _to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        avatar_url=user.avatar_url,
        timezone=user.timezone,
        role=user.role,
        is_admin=user.role == "admin",
        email_verified=user.email_verified_at is not None,
        has_password=user.password_hash is not None,
        providers=[i.provider for i in (user.identities or [])],
        created_at=user.created_at,
    )


async def _respond_with_session(
    db: AsyncSession, user: User, request: Request, response: Response
) -> AuthResponse:
    access, refresh = await AuthService.issue_session(db, user, request)
    set_auth_cookies(response, access, refresh)
    return AuthResponse(
        user=_to_user_response(user),
        access_token=access,
        expires_in=settings.ACCESS_TOKEN_MINUTES * 60,
    )


# ------------------------------------------------------ email + password


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(10, 3600, "register"))],
    summary="Create an account",
)
async def register(
    data: RegisterRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    user = await AuthService.register(db, data.name, data.email, data.password)
    token = sign_purpose_token("verify-email", str(user.id), minutes=60 * 24)
    # No mail provider is wired up yet, so the link is logged rather than sent.
    logger.info("Email verification link for %s: %s/verify-email?token=%s", user.email, settings.PUBLIC_APP_URL, token)
    return await _respond_with_session(db, user, request, response)


@router.post(
    "/login",
    response_model=AuthResponse,
    dependencies=[Depends(RateLimiter(10, 300, "login"))],
    summary="Sign in",
)
async def login(
    data: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    user = await AuthService.authenticate(db, data.email, data.password)
    return await _respond_with_session(db, user, request, response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Sign out")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        # Revoked server-side, not just cleared client-side.
        await AuthService.revoke(db, token)
    clear_auth_cookies(response)
    return None


@router.post("/refresh", response_model=AuthResponse, summary="Rotate the session")
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No session.")
    access, new_refresh, user = await AuthService.rotate(db, token, request)
    set_auth_cookies(response, access, new_refresh)
    return AuthResponse(
        user=_to_user_response(user), access_token=access, expires_in=settings.ACCESS_TOKEN_MINUTES * 60
    )


@router.get("/me", response_model=UserResponse, summary="The signed-in user")
async def me(user: User = Depends(current_user)):
    return _to_user_response(user)


@router.post(
    "/forgot-password",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(RateLimiter(5, 900, "forgot"))],
    summary="Request a password reset",
)
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    user = await AuthService.get_by_email(db, data.email)
    if user:
        token = sign_purpose_token("reset-password", str(user.id), minutes=30)
        logger.info("Password reset link for %s: %s/reset-password?token=%s", user.email, settings.PUBLIC_APP_URL, token)
    # Always the same reply: a different one would confirm the address exists.
    return {"message": "If that email is registered, a reset link is on its way."}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT, summary="Set a new password")
async def reset_password(data: ResetPasswordRequest, response: Response, db: AsyncSession = Depends(get_db)):
    subject = read_purpose_token("reset-password", data.token)
    if not subject:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That reset link is invalid or has expired.")
    user = await db.get(User, int(subject))
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That reset link is invalid or has expired.")

    user.password_hash = hash_password(data.password)
    await db.commit()
    # Anyone holding a stolen session loses it here.
    await AuthService.revoke_all(db, user.id)
    clear_auth_cookies(response)
    return None


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT, summary="Confirm an email address")
async def verify_email(data: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    subject = read_purpose_token("verify-email", data.token)
    if not subject:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That verification link is invalid or has expired.")
    user = await db.get(User, int(subject))
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That verification link is invalid or has expired.")
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(timezone.utc)
        await db.commit()
    return None


# ------------------------------------------------------------------ oauth


def _provider_or_404(provider: str) -> dict:
    if provider not in PROVIDERS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown provider '{provider}'.")
    enabled = settings.google_enabled if provider == "google" else settings.github_enabled
    if not enabled:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"{provider.title()} sign-in is not configured on this server.",
        )
    return PROVIDERS[provider]


def _redirect_uri(provider: str) -> str:
    return f"{settings.PUBLIC_API_URL.rstrip('/')}/api/v1/auth/oauth/{provider}/callback"


def _safe_return_to(value: Optional[str]) -> str:
    """Only same-site paths. An absolute URL here would be an open redirect."""
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return "/my-letters"


@router.get("/oauth/{provider}", summary="Begin OAuth sign-in")
async def oauth_start(provider: str, return_to: Optional[str] = None):
    conf = _provider_or_404(provider)

    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    _pending[state] = (verifier, _safe_return_to(return_to))

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID if provider == "google" else settings.GITHUB_CLIENT_ID,
        "redirect_uri": _redirect_uri(provider),
        "response_type": "code",
        "scope": conf["scope"],
        "state": state,
    }
    if provider == "google":
        # Authorization Code + PKCE. No implicit flow.
        params |= {
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "select_account",
        }
    return RedirectResponse(f"{conf['authorize']}?{urlencode(params)}", status_code=302)


@router.get("/oauth/{provider}/callback", summary="OAuth redirect target")
async def oauth_callback(
    provider: str,
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    conf = _provider_or_404(provider)
    app_url = settings.PUBLIC_APP_URL.rstrip("/")

    def fail(reason: str) -> RedirectResponse:
        return RedirectResponse(f"{app_url}/login?error={reason}", status_code=302)

    if error or not code or not state:
        return fail("oauth_cancelled")

    # Consumed here, so a replayed state cannot be reused.
    pending = _pending.pop(state, None)
    if pending is None:
        return fail("bad_state")
    verifier, return_to = pending

    data = {
        "client_id": settings.GOOGLE_CLIENT_ID if provider == "google" else settings.GITHUB_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET if provider == "google" else settings.GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": _redirect_uri(provider),
        "grant_type": "authorization_code",
    }
    if provider == "google":
        data["code_verifier"] = verifier

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            token_res = await client.post(conf["token"], data=data, headers={"Accept": "application/json"})
            token_res.raise_for_status()
            tokens = token_res.json()
            access = tokens.get("access_token")
            if not access:
                return fail("token_exchange_failed")

            profile_res = await client.get(
                conf["userinfo"], headers={"Authorization": f"Bearer {access}", "Accept": "application/json"}
            )
            profile_res.raise_for_status()
            profile = profile_res.json()

            email = profile.get("email")
            if provider == "github" and not email:
                # GitHub omits a private email from /user; ask explicitly.
                emails = (await client.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"Bearer {access}", "Accept": "application/json"},
                )).json()
                primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
                email = primary.get("email") if primary else None
    except httpx.HTTPError:
        logger.exception("OAuth exchange failed for %s", provider)
        return fail("provider_unreachable")

    account_id = str(profile.get("sub") or profile.get("id") or "")
    if not account_id:
        return fail("no_account_id")

    try:
        user = await AuthService.link_or_create(
            db,
            provider=provider,
            provider_account_id=account_id,
            email=email,
            name=profile.get("name") or profile.get("login"),
            avatar_url=profile.get("picture") or profile.get("avatar_url"),
            access_token=access,
            refresh_token=tokens.get("refresh_token"),
        )
    except HTTPException:
        return fail("link_failed")

    access_token, refresh_token = await AuthService.issue_session(db, user, request)
    redirect = RedirectResponse(f"{app_url}{return_to}", status_code=302)
    set_auth_cookies(redirect, access_token, refresh_token)
    return redirect


@router.get("/providers", summary="Which OAuth providers are configured")
async def providers():
    return {"google": settings.google_enabled, "github": settings.github_enabled}
