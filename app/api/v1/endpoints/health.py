from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health", summary="API Health Check")
async def health_check():
    return {
        "status": "healthy",
        "project_name": settings.PROJECT_NAME,
        "api_v1_str": settings.API_V1_STR,
        "database": "connected",
    }
