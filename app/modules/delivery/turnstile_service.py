import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class TurnstileService:
    """Service to verify Cloudflare Turnstile CAPTCHA tokens."""

    VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

    @classmethod
    async def verify_token(
        cls,
        token: str,
        remote_ip: Optional[str] = None,
    ) -> bool:
        """Verify a Cloudflare Turnstile response token.

        Returns True if Turnstile is disabled (TURNSTILE_SECRET_KEY not set)
        or if token verification succeeds with Cloudflare.
        """
        if not settings.turnstile_enabled:
            logger.info("TURNSTILE_SECRET_KEY is not configured. Bypassing Turnstile token check.")
            return True

        if not token:
            logger.warning("Empty Turnstile response token provided.")
            return False

        payload = {
            "secret": settings.TURNSTILE_SECRET_KEY,
            "response": token,
        }
        if remote_ip:
            payload["remoteip"] = remote_ip

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    cls.VERIFY_URL,
                    data=payload,
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()

                success = data.get("success", False)
                if not success:
                    error_codes = data.get("error-codes", [])
                    logger.warning(
                        "Cloudflare Turnstile token validation failed. Error codes: %s",
                        error_codes,
                    )
                return bool(success)
        except Exception as e:
            logger.error("Error during Cloudflare Turnstile token verification: %s", str(e))
            return False
