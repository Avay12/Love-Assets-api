"""Backwards-compatibility shim re-exporting models from domain modules."""

from app.modules.auth.models import OAuthIdentity, Session, User
from app.modules.letters.models import Letter
from app.modules.templates.models import Template

__all__ = ["User", "OAuthIdentity", "Session", "Letter", "Template"]
