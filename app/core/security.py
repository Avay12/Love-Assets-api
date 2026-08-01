import secrets
import hashlib
from typing import Optional


def generate_secure_token(length: int = 32) -> str:
    """Generates a cryptographically secure random token string."""
    return secrets.token_hex(length // 2)


def hash_contact_info(contact: str) -> str:
    """Hashes recipient contact info for privacy protection if needed."""
    return hashlib.sha256(contact.strip().lower().encode("utf-8")).hexdigest()
