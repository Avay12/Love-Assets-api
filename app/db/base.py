"""Imports every model so `Base.metadata` is complete.

Alembic's --autogenerate diffs against this metadata. A model that is not
imported here is invisible to it, which is how `payments` and
`letters.user_id` ended up with no migration.
"""

from app.core.database import Base
from app.modules.auth.models import OAuthIdentity, Session, User
from app.modules.letters.models import Letter
from app.modules.payments.models import Payment
from app.modules.templates.models import Template

__all__ = ["Base", "User", "OAuthIdentity", "Session", "Letter", "Payment", "Template"]
