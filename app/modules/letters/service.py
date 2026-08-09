import random
import secrets
import string
from typing import List, Optional, Tuple

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.delivery.seven_service import SevenService
from app.modules.letters.models import Letter
from app.modules.letters.schemas import (
    LetterCommon,
    LetterCreate,
    LetterUpdate,
    TypedLetterResponse,
)

SLUG_PREFIX = {
    "love": "love",
    "valentine": "val",
    "birthday": "bday",
    "birthday-invite": "party",
    "wedding": "wed",
}

_ALPHABET = string.ascii_lowercase + string.digits


def generate_slug(letter_type: str = "love", length: int = 10) -> str:
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


class LetterService:
    @staticmethod
    async def create_letter(db: AsyncSession, data: LetterCreate) -> Letter:
        slug_prefix = "birthday" if data.type == "birthday" else "love"
        slug = generate_slug(slug_prefix)

        existing = await db.scalar(select(Letter).where(Letter.slug == slug))
        while existing:
            slug = generate_slug(slug_prefix)
            existing = await db.scalar(select(Letter).where(Letter.slug == slug))

        letter = Letter(
            slug=slug,
            type=data.type,
            template_id=data.template_id,
            from_name=data.from_name,
            to_name=data.to_name,
            message=data.message,
            photos=data.photos,
            song_id=data.song_id,
            song_title=data.song_title,
            song_artist=data.song_artist,
            song_preview_url=data.song_preview_url,
            delivery_method=data.delivery_method,
            delivery_contact=data.delivery_contact,
            scheduled_at=data.scheduled_at,
        )

        db.add(letter)
        await db.commit()
        await db.refresh(letter)

        if data.delivery_method == "sms" and data.delivery_contact:
            text = f"You received a {data.type} letter from {data.from_name}! View it here: {settings.PUBLIC_APP_URL.rstrip('/')}/l/{letter.slug}"
            await SevenService.send_sms(to=data.delivery_contact, text=text, delay=data.scheduled_at)
        elif data.delivery_method == "call" and data.delivery_contact:
            text = f"Hello {data.to_name}, you have a new {data.type} letter from {data.from_name}."
            await SevenService.send_voice(to=data.delivery_contact, text=text, delay=data.scheduled_at)

        return letter

    @staticmethod
    async def get_letter_by_slug(db: AsyncSession, slug: str) -> Optional[Letter]:
        result = await db.execute(select(Letter).where(Letter.slug == slug))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_letter_by_id(db: AsyncSession, letter_id: int) -> Optional[Letter]:
        result = await db.execute(select(Letter).where(Letter.id == letter_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_letters(
        db: AsyncSession, skip: int = 0, limit: int = 20, type_filter: Optional[str] = None
    ) -> Tuple[List[Letter], int]:
        query = select(Letter)
        count_query = select(func.count()).select_from(Letter)

        if type_filter:
            query = query.where(Letter.type == type_filter)
            count_query = count_query.where(Letter.type == type_filter)

        total = (await db.execute(count_query)).scalar() or 0
        result = await db.execute(query.order_by(Letter.created_at.desc()).offset(skip).limit(limit))
        letters = result.scalars().all()
        return list(letters), total

    @staticmethod
    async def update_letter(db: AsyncSession, slug: str, data: LetterUpdate) -> Optional[Letter]:
        letter = await LetterService.get_letter_by_slug(db, slug)
        if not letter:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(letter, key, value)

        await db.commit()
        await db.refresh(letter)
        return letter

    @staticmethod
    async def delete_letter(db: AsyncSession, slug: str) -> bool:
        letter = await LetterService.get_letter_by_slug(db, slug)
        if not letter:
            return False
        await db.delete(letter)
        await db.commit()
        return True


class TypedLetterService:
    @staticmethod
    async def create(
        db: AsyncSession, letter_type: str, data: LetterCommon, user_id: Optional[int] = None
    ) -> TypedLetterResponse:
        details = data.details.model_dump(mode="json", exclude_none=True) if hasattr(data, "details") else {}
        if data.artwork:
            details["_artwork"] = data.artwork

        letter = Letter(
            slug=generate_slug(letter_type),
            user_id=user_id,
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

        # Create payment record
        from app.modules.payments.models import Payment
        pay_code = f"PAY-{secrets.randbelow(9000) + 1000}"
        payment = Payment(
            payment_code=pay_code,
            user_id=user_id,
            letter_id=letter.id,
            amount=4.99,
            currency="USD",
            payment_method="Card",
            status="Paid",
        )
        db.add(payment)
        try:
            await db.commit()
        except Exception:
            await db.rollback()

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
    async def get_by_slug(db: AsyncSession, slug: str, letter_type: Optional[str] = None) -> Optional[TypedLetterResponse]:
        query = select(Letter).where(Letter.slug == slug)
        if letter_type:
            query = query.where(Letter.type == letter_type)
        letter = await db.scalar(query)
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
