from fastapi import APIRouter
from app.api.v1.router import api_router as v1_router
from app.core.config import settings

main_router = APIRouter()
main_router.include_router(v1_router, prefix=settings.API_V1_STR)
