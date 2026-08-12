import secrets
import string
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.delivery.email_service import EmailService
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


async def notify_recipient(letter: Letter) -> None:
    """Hand the share link to the recipient over the chosen channel.

    "link" is a no-op by design: the sender passes the URL on themselves.
    Every sender returns False rather than raising when its integration is
    unconfigured, so a missing API key never fails letter creation.
    """
    if not letter.delivery_contact or letter.delivery_method == "link":
        return
    link = share_url_for(letter.slug)

    if letter.delivery_method == "email":
        await EmailService.send_letter(
            to_email=letter.delivery_contact,
            from_name=letter.from_name,
            to_name=letter.to_name,
            link=link,
        )
    elif letter.delivery_method == "sms":
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
    async def create_letter(db: AsyncSession, data: LetterCreate, user_id: Optional[int] = None) -> Letter:
        slug_prefix = "birthday" if data.type == "birthday" else "love"
        slug = generate_slug(slug_prefix)

        existing = await db.scalar(select(Letter).where(Letter.slug == slug))
        while existing:
            slug = generate_slug(slug_prefix)
            existing = await db.scalar(select(Letter).where(Letter.slug == slug))

        letter = Letter(
            slug=slug,
            user_id=user_id,
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

        await notify_recipient(letter)
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
    async def apply_update(db: AsyncSession, letter: Letter, data: LetterUpdate) -> Letter:
        """Write a patch onto a letter the caller has already been authorised
        for -- the ownership check lives in the router."""
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(letter, key, value)
        await db.commit()
        await db.refresh(letter)
        return letter


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

        # Record the order. No payment gateway is wired up yet, so this opens
        # as "Pending" and stays there -- nothing here has taken any money, and
        # writing "Paid" would put invented revenue on the admin dashboard.
        from app.modules.payments.models import Payment

        payment = Payment(
            payment_code=f"PAY-{secrets.token_hex(4).upper()}",
            user_id=user_id,
            letter_id=letter.id,
            amount=settings.LETTER_PRICE,
            currency=settings.LETTER_CURRENCY,
            payment_method="Card",
            status="Pending",
        )
        db.add(payment)
        try:
            await db.commit()
        except Exception:
            await db.rollback()

        await notify_recipient(letter)
        return to_response(letter)

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
