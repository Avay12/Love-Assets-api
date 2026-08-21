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


_DEFAULT_PRICING = {
    "link": 1.0,
    "email": 2.0,
    "sms": 3.0,
    "call": 4.0,
}
_current_pricing = dict(_DEFAULT_PRICING)


class DeliveryService:
    @staticmethod
    def get_pricing() -> dict:
        return dict(_current_pricing)

    @staticmethod
    def update_pricing(pricing: "DeliveryPricing") -> dict:
        global _current_pricing
        _current_pricing["link"] = round(float(pricing.link), 2)
        _current_pricing["email"] = round(float(pricing.email), 2)
        _current_pricing["sms"] = round(float(pricing.sms), 2)
        _current_pricing["call"] = round(float(pricing.call), 2)
        return dict(_current_pricing)

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
