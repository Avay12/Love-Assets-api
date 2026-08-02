import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service to send transactional emails via SMTP (Brevo / Sendinblue)."""

    @classmethod
    def _send_smtp(cls, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        if not settings.smtp_enabled:
            logger.warning("SMTP credentials not configured (SMTP_USER / SMTP_PASSWORD missing). Skipping email delivery.")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.MAIL_FROM
        msg["To"] = to_email

        if text_content:
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            logger.info("Successfully sent email '%s' to %s via Brevo SMTP", subject, to_email)
            return True
        except Exception:
            logger.exception("Failed to send email to %s via Brevo SMTP", to_email)
            return False

    @classmethod
    async def send_email(cls, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """Asynchronous wrapper to prevent blocking the FastAPI event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, cls._send_smtp, to_email, subject, html_content, text_content
        )
