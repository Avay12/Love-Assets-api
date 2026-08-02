from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.delivery.schemas import DeliveryRequest, DeliveryResponse
from app.modules.delivery.seven_service import SevenService
from app.modules.letters.service import LetterService


class DeliveryService:
    @staticmethod
    async def process_delivery(db: AsyncSession, request: DeliveryRequest) -> DeliveryResponse:
        letter = await LetterService.get_letter_by_slug(db, request.letter_slug)
        if not letter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Letter with slug '{request.letter_slug}' not found"
            )

        letter.delivery_method = request.method
        if request.contact:
            letter.delivery_contact = request.contact
        if request.scheduled_at:
            letter.scheduled_at = request.scheduled_at

        await db.commit()

        if request.method == "link":
            msg = f"Private link ready for letter '{letter.slug}'."
        elif request.method == "email":
            msg = f"Email delivery scheduled for '{request.contact or 'recipient'}'."
        elif request.method == "sms":
            msg = f"SMS notification scheduled for '{request.contact or 'recipient'}'."
            if request.contact:
                text = f"You received a letter from {letter.from_name}! View it here: {settings.PUBLIC_APP_URL.rstrip('/')}/l/{letter.slug}"
                await SevenService.send_sms(to=request.contact, text=text, delay=request.scheduled_at)
        elif request.method == "call":
            msg = f"Voice call reading queued for '{request.contact or 'recipient'}'."
            if request.contact:
                text = f"Hello {letter.to_name}, you have a new letter from {letter.from_name}."
                await SevenService.send_voice(to=request.contact, text=text, delay=request.scheduled_at)
        else:
            msg = "Delivery option recorded successfully."

        return DeliveryResponse(
            success=True,
            message=msg,
            letter_slug=letter.slug,
            method=request.method,
            contact=request.contact,
            scheduled_at=request.scheduled_at,
        )
