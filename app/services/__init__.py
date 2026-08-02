"""Backwards-compatibility shim re-exporting services from domain modules."""

from app.modules.auth.service import AuthService
from app.modules.delivery.email_service import EmailService
from app.modules.delivery.service import DeliveryService
from app.modules.delivery.seven_service import SevenService
from app.modules.delivery.turnstile_service import TurnstileService
from app.modules.letters.service import LetterService, TypedLetterService
from app.modules.music.service import MusicService
from app.modules.templates.service import TemplateService

__all__ = [
    "AuthService",
    "DeliveryService",
    "EmailService",
    "SevenService",
    "TurnstileService",
    "LetterService",
    "TypedLetterService",
    "MusicService",
    "TemplateService",
]
