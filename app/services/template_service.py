from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.template import Template
from app.schemas.template import TemplateResponse

DEFAULT_TEMPLATES = [
    {
        "id": "mailbox",
        "title": "3D Mailbox",
        "subtitle": "Lavender Garden",
        "body": "Open the vintage garden mailbox, unseal the envelope, and watch a handwritten photo letter type itself out with music.",
        "type": "love",
        "experience": "photo",
        "image_url": "/assets/mailbox-closed.jpg",
        "is_premium": False,
        "is_birthday_exclusive": False,
    },
    {
        "id": "paper",
        "title": "Realistic Paper",
        "subtitle": "Fold-Open 3D",
        "body": "A realistic paper letter experience that gracefully unfolds with customized handwriting and photos.",
        "type": "love",
        "experience": "paper",
        "image_url": "/assets/letter-flatlay.jpg",
        "is_premium": True,
        "is_birthday_exclusive": False,
    },
    {
        "id": "envelope",
        "title": "Premium Envelope",
        "subtitle": "Rose Classic",
        "body": "A luxury rose envelope experience featuring interactive unsealing and elegant typography.",
        "type": "love",
        "experience": "purple",
        "image_url": "/assets/hero-letters.jpg",
        "is_premium": False,
        "is_birthday_exclusive": False,
    },
    {
        "id": "birthday-mailbox",
        "title": "Birthday Mailbox",
        "subtitle": "Festive Reveal",
        "body": "A festive mailbox reveal, a balloon pop game, and a heartfelt personal letter — all in one magical birthday experience.",
        "type": "birthday",
        "experience": "purple",
        "image_url": "/assets/birthday-mailbox-closed.jpg",
        "is_premium": False,
        "is_birthday_exclusive": True,
    },
]


class TemplateService:
    @staticmethod
    async def seed_templates_if_empty(db: AsyncSession) -> None:
        result = await db.execute(select(Template))
        existing = result.scalars().all()
        if not existing:
            for tpl in DEFAULT_TEMPLATES:
                template_obj = Template(**tpl)
                db.add(template_obj)
            await db.commit()

    @staticmethod
    async def get_templates(
        db: AsyncSession, type_filter: Optional[str] = None
    ) -> List[TemplateResponse]:
        await TemplateService.seed_templates_if_empty(db)
        query = select(Template)
        if type_filter:
            query = query.where(Template.type == type_filter)
        
        result = await db.execute(query)
        templates = result.scalars().all()
        return [TemplateResponse.model_validate(t) for t in templates]

    @staticmethod
    async def get_template_by_id(db: AsyncSession, template_id: str) -> Optional[TemplateResponse]:
        await TemplateService.seed_templates_if_empty(db)
        result = await db.execute(select(Template).where(Template.id == template_id))
        template = result.scalar_one_or_none()
        if template:
            return TemplateResponse.model_validate(template)
        return None
