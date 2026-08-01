import random
import string
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from app.db.models.letter import Letter
from app.schemas.letter import LetterCreate, LetterUpdate
from app.core.config import settings
from app.services.seven_service import SevenService


def generate_slug(prefix: str = "love") -> str:
    chars = string.ascii_lowercase + string.digits
    random_part = "".join(random.choices(chars, k=6))
    clean_prefix = "bday" if prefix == "birthday" else "love"
    return f"{clean_prefix}-{random_part}"


class LetterService:
    @staticmethod
    async def create_letter(db: AsyncSession, data: LetterCreate) -> Letter:
        slug_prefix = "birthday" if data.type == "birthday" else "love"
        slug = generate_slug(slug_prefix)

        # Check slug uniqueness just in case
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
