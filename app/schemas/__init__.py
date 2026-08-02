"""Backwards-compatibility shim re-exporting schemas from domain modules."""

from app.modules.auth.schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.modules.delivery.schemas import DeliveryRequest, DeliveryResponse
from app.modules.letters.schemas import LetterCreate, LetterListResponse, LetterResponse, LetterUpdate
from app.modules.media.schemas import FileUploadResponse
from app.modules.music.schemas import MusicSearchResponse, TrackResult
from app.modules.templates.schemas import TemplateListResponse, TemplateResponse

__all__ = [
    "AuthResponse",
    "LoginRequest",
    "RegisterRequest",
    "UserResponse",
    "DeliveryRequest",
    "DeliveryResponse",
    "LetterCreate",
    "LetterListResponse",
    "LetterResponse",
    "LetterUpdate",
    "FileUploadResponse",
    "MusicSearchResponse",
    "TrackResult",
    "TemplateListResponse",
    "TemplateResponse",
]
