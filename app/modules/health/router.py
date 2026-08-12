from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

router = APIRouter()


@router.get("/health", summary="API Health Check")
async def health_check(response: Response, db: AsyncSession = Depends(get_db)):
    """Actually touches the database. A health check that reports "connected"
    without a query is worse than none -- it stays green through an outage."""
    try:
        await db.execute(text("SELECT 1"))
        database = "connected"
    except Exception:
        database = "unavailable"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "healthy" if database == "connected" else "degraded",
        "project_name": settings.PROJECT_NAME,
        "api_v1_str": settings.API_V1_STR,
        "database": database,
    }
