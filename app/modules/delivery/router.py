from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import current_user
from app.modules.auth.models import User
from app.modules.delivery.schemas import DeliveryPricing, DeliveryRequest, DeliveryResponse
from app.modules.delivery.service import DeliveryService
from app.modules.letters.router import load_owned_letter

router = APIRouter()


@router.post(
    "/schedule",
    response_model=DeliveryResponse,
    status_code=status.HTTP_200_OK,
    summary="Schedule letter delivery",
)
async def schedule_delivery(
    request: DeliveryRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    letter = await load_owned_letter(db, request.letter_slug, user)
    return await DeliveryService.process_delivery(db, letter, request)


@router.get(
    "/pricing",
    response_model=DeliveryPricing,
    status_code=status.HTTP_200_OK,
    summary="Get current delivery prices",
)
async def get_delivery_pricing():
    return DeliveryService.get_pricing()
