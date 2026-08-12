import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr
from html import escape
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _shell(heading: str, body_html: str, button_label: str, button_url: str) -> str:
    """One inline-styled layout for every transactional email -- mail clients
    strip <style> blocks, so the rules have to live on the elements."""
    return f"""\
<div style="margin:0;padding:32px 16px;background:#fdf7f4;font-family:Georgia,'Times New Roman',serif;color:#3b2f2f">
  <div style="max-width:520px;margin:0 auto;background:#fffdfb;border:1px solid #f0e2da;border-radius:24px;padding:40px 32px">
    <p style="margin:0 0 24px;font-size:13px;letter-spacing:.2em;text-transform:uppercase;color:#d4667a">Wish2Love</p>
    <h1 style="margin:0 0 16px;font-size:26px;line-height:1.3;font-weight:normal">{heading}</h1>
    {body_html}
    <a href="{button_url}"
       style="display:inline-block;margin:28px 0 8px;padding:14px 32px;border-radius:999px;background:#d4667a;color:#fff;text-decoration:none;font-weight:bold">
      {button_label}
    </a>
    <p style="margin:24px 0 0;font-size:13px;color:#8b7a75;word-break:break-all">
      If the button does not work, paste this into your browser:<br>{button_url}
    </p>
  </div>
</div>"""


class EmailService:
    """Transactional email over SMTP (Brevo / Sendinblue)."""

    @classmethod
    def _send_smtp(
        cls, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None
    ) -> bool:
        if not settings.smtp_enabled:
            logger.warning(
                "SMTP credentials not configured (SMTP_USER / SMTP_PASSWORD missing). "
                "Skipping email to %s.",
                to_email,
            )
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
            logger.info("Sent email '%s' to %s", subject, to_email)
            return True
        except Exception:
            logger.exception("Failed to send email to %s", to_email)
            return False

    @classmethod
    async def send_email(
        cls, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None
    ) -> bool:
        """smtplib is blocking, so it runs off the event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, cls._send_smtp, to_email, subject, html_content, text_content
        )

    # ------------------------------------------------------------ templates

    @classmethod
    async def send_password_reset(cls, to_email: str, name: str, link: str) -> bool:
        html = _shell(
            heading=f"Hello {escape(name)},",
            body_html=(
                "<p style='margin:0;font-size:16px;line-height:1.6'>Someone asked to reset the password "
                "on your Wish2Love account. This link works once and expires in 30 minutes.</p>"
                "<p style='margin:12px 0 0;font-size:16px;line-height:1.6'>If it was not you, ignore this "
                "email — nothing has changed.</p>"
            ),
            button_label="Choose a new password",
            button_url=link,
        )
        text = (
            f"Hello {name},\n\n"
            f"Reset your Wish2Love password here (valid for 30 minutes):\n{link}\n\n"
            "If you did not ask for this, ignore this email."
        )
        return await cls.send_email(to_email, "Reset your Wish2Love password", html, text)

    @classmethod
    async def send_invite(cls, to_email: str, link: str) -> bool:
        html = _shell(
            heading="You have been invited to Wish2Love.",
            body_html=(
                "<p style='margin:0;font-size:16px;line-height:1.6'>An account has been created for you. "
                "Pick a password to finish setting it up — this link is good for a week.</p>"
            ),
            button_label="Set your password",
            button_url=link,
        )
        text = f"You have been invited to Wish2Love. Set your password here (valid 7 days):\n{link}"
        return await cls.send_email(to_email, "Your Wish2Love invitation", html, text)

    @classmethod
    async def send_letter(cls, to_email: str, from_name: str, to_name: str, link: str) -> bool:
        sender = escape(from_name)
        html = _shell(
            heading=f"{escape(to_name)}, you have a letter.",
            body_html=(
                f"<p style='margin:0;font-size:16px;line-height:1.6'><strong>{sender}</strong> wrote you "
                "something and asked us to hand it over. Open it whenever you have a quiet minute.</p>"
            ),
            button_label="Open your letter",
            button_url=link,
        )
        text = f"{to_name}, {from_name} sent you a letter. Open it here:\n{link}"
        # Reply-to is meaningless here (no-reply sender), so keep it simple.
        return await cls.send_email(to_email, f"{from_name} sent you a letter", html, text)


def sender_display_name() -> str:
    """The human-readable half of MAIL_FROM, for logs and previews."""
    name, addr = parseaddr(settings.MAIL_FROM)
    return formataddr((name or "Wish2Love", addr))
