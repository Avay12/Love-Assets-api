import logging
from datetime import datetime
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class SevenService:
    BASE_URL = "https://gateway.seven.io/api"

    @classmethod
    async def _send_request(cls, endpoint: str, payload: dict) -> bool:
        if not settings.SEVEN_API_KEY:
            logger.warning("SEVEN_API_KEY is not set. Skipping sending.")
            return False

        headers = {
            "X-Api-Key": settings.SEVEN_API_KEY,
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{cls.BASE_URL}/{endpoint}",
                    headers=headers,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                logger.info(f"Successfully sent {endpoint} via Seven.io")
                return True
            except Exception as e:
                logger.error(f"Failed to send {endpoint} via Seven.io: {str(e)}")
                return False

    @classmethod
    async def send_sms(cls, to: str, text: str, delay: Optional[datetime] = None) -> bool:
        payload = {"to": to, "text": text}
        if delay:
            payload["delay"] = delay.strftime("%Y-%m-%d %H:%M:%S")
        return await cls._send_request("sms", payload)

    @classmethod
    async def send_voice(cls, to: str, text: str, delay: Optional[datetime] = None) -> bool:
        payload = {"to": to, "text": text}
        if delay:
            payload["delay"] = delay.strftime("%Y-%m-%d %H:%M:%S")
        return await cls._send_request("voice", payload)
