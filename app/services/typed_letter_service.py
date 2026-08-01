"""Creation and lookup for the five letter types.

All types persist to the same ``letters`` row; the per-type payload lives in
``Letter.details``. Keeping one table avoids five near-identical schemas while
the per-type Pydantic models still enforce the right shape at the edge.
"""

import secrets
import string
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.letter import Letter
from app.schemas.letter_types import LetterCommon, TypedLetterResponse
from app.services.seven_service import SevenService

# Slug prefix per type, so a link hints at what it opens.
SLUG_PREFIX = {
    "love": "love",
    "valentine": "val",
    "birthday": "bday",
    "birthday-invite": "party",
    "wedding": "wed",
}

_ALPHABET = string.ascii_lowercase + string.digits


def generate_slug(letter_type: str, length: int = 10) -> str:
    """Unguessable slug.

    The slug is the only thing protecting a letter, so this uses ``secrets``
    rather than ``random`` (Mersenne Twister is predictable from prior output),
    and 10 chars over 36 symbols instead of 6.
    """
    prefix = SLUG_PREFIX.get(letter_type, "love")
    body = "".join(secrets.choice(_ALPHABET) for _ in range(length))
    return f"{prefix}-{body}"


def share_url_for(slug: str) -> str:
    return f"{settings.PUBLIC_APP_URL.rstrip('/')}/l/{slug}"


def to_response(letter: Letter) -> TypedLetterResponse:
    return TypedLetterResponse(
        id=letter.id,
        slug=letter.slug,
        type=letter.type,
        share_url=share_url_for(letter.slug),
        template_id=letter.template_id,
        from_name=letter.from_name,
        to_name=letter.to_name,
        message=letter.message,
        photos=letter.photos or [],
        song_id=letter.song_id,
        song_title=letter.song_title,
        song_artist=letter.song_artist,
        song_preview_url=letter.song_preview_url,
        artwork=(letter.details or {}).get("_artwork"),
        delivery_method=letter.delivery_method,
        delivery_contact=letter.delivery_contact,
        scheduled_at=letter.scheduled_at,
        details={k: v for k, v in (letter.details or {}).items() if not k.startswith("_")},
        created_at=letter.created_at,
        updated_at=letter.updated_at,
    )


class TypedLetterService:
    @staticmethod
    async def create(db: AsyncSession, letter_type: str, data: LetterCommon) -> TypedLetterResponse:
        details = data.details.model_dump(mode="json", exclude_none=True) if hasattr(data, "details") else {}
        if data.artwork:
            # underscore-prefixed keys are internal and stripped from responses
            details["_artwork"] = data.artwork

        letter = Letter(
            slug=generate_slug(letter_type),
            type=letter_type,
            template_id=data.template_id,
            from_name=data.from_name,
            to_name=data.to_name,
            message=data.message,
            photos=data.photos,
            details=details,
            song_id=data.song_id,
            song_title=data.song_title,
            song_artist=data.song_artist,
            song_preview_url=data.song_preview_url,
            delivery_method=data.delivery_method,
            delivery_contact=data.delivery_contact,
            scheduled_at=data.scheduled_at,
        )

        # Retry on the unique constraint rather than SELECT-then-INSERT, which
        # is a race under concurrency.
        for attempt in range(5):
            try:
                db.add(letter)
                await db.commit()
                break
            except IntegrityError:
                await db.rollback()
                if attempt == 4:
                    raise
                letter.slug = generate_slug(letter_type)
        await db.refresh(letter)

        await TypedLetterService._notify(letter)
        return to_response(letter)

    @staticmethod
    async def _notify(letter: Letter) -> None:
        if not letter.delivery_contact:
            return
        link = share_url_for(letter.slug)
        if letter.delivery_method == "sms":
            await SevenService.send_sms(
                to=letter.delivery_contact,
                text=f"{letter.from_name} sent you something. Open it here: {link}",
                delay=letter.scheduled_at,
            )
        elif letter.delivery_method == "call":
            await SevenService.send_voice(
                to=letter.delivery_contact,
                text=f"Hello {letter.to_name}, you have a new message from {letter.from_name}.",
                delay=letter.scheduled_at,
            )

    @staticmethod
    async def get_by_slug(db: AsyncSession, slug: str) -> Optional[TypedLetterResponse]:
        letter = await db.scalar(select(Letter).where(Letter.slug == slug))
        return to_response(letter) if letter else None

    @staticmethod
    async def list_by_type(
        db: AsyncSession, letter_type: str, skip: int = 0, limit: int = 20
    ) -> Tuple[List[TypedLetterResponse], int]:
        total = (
            await db.scalar(select(func.count()).select_from(Letter).where(Letter.type == letter_type))
        ) or 0
        rows = (
            await db.execute(
                select(Letter)
                .where(Letter.type == letter_type)
                .order_by(Letter.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
        ).scalars().all()
        return [to_response(r) for r in rows], total

    @staticmethod
    async def delete_by_slug(db: AsyncSession, slug: str, letter_type: str) -> bool:
        letter = await db.scalar(select(Letter).where(Letter.slug == slug, Letter.type == letter_type))
        if not letter:
            return False
        await db.delete(letter)
        await db.commit()
        return True
