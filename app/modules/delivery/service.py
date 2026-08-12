from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.delivery.schemas import DeliveryRequest, DeliveryResponse
from app.modules.letters.models import Letter
from app.modules.letters.service import notify_recipient

_MESSAGES = {
    "link": "Private link ready for letter '{slug}'.",
    "email": "Email delivery scheduled for '{contact}'.",
    "sms": "SMS notification scheduled for '{contact}'.",
    "call": "Voice call reading queued for '{contact}'.",
}


class DeliveryService:
    @staticmethod
    async def process_delivery(db: AsyncSession, letter: Letter, request: DeliveryRequest) -> DeliveryResponse:
        """Re-target a letter's delivery. The caller must already have been
        authorised for this letter -- ownership is checked in the router,
        because anyone who can point this at an arbitrary slug can send SMS and
        voice calls to a number of their choosing on our account."""
        letter.delivery_method = request.method
        if request.contact:
            letter.delivery_contact = request.contact
        if request.scheduled_at:
            letter.scheduled_at = request.scheduled_at

        await db.commit()
        await db.refresh(letter)

        await notify_recipient(letter)

        template = _MESSAGES.get(request.method, "Delivery option recorded successfully.")
        return DeliveryResponse(
            success=True,
            message=template.format(slug=letter.slug, contact=request.contact or "recipient"),
            letter_slug=letter.slug,
            method=request.method,
            contact=request.contact,
            scheduled_at=request.scheduled_at,
        )
