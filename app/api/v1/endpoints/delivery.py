from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.delivery import DeliveryRequest, DeliveryResponse
from app.services.delivery_service import DeliveryService

router = APIRouter()


@router.post("/schedule", response_model=DeliveryResponse, status_code=status.HTTP_200_OK, summary="Schedule letter delivery")
async def schedule_delivery(
    request: DeliveryRequest,
    db: AsyncSession = Depends(get_db)
):
    return await DeliveryService.process_delivery(db, request)
