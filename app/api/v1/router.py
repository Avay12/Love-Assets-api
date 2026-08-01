from fastapi import APIRouter

from app.api.v1.endpoints import (
    health,
    letters,
    templates,
    music,
    media,
    delivery,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(letters.router, prefix="/letters", tags=["Letters"])
api_router.include_router(templates.router, prefix="/templates", tags=["Templates"])
api_router.include_router(music.router, prefix="/music", tags=["Music"])
api_router.include_router(media.router, prefix="/media", tags=["Media"])
api_router.include_router(delivery.router, prefix="/delivery", tags=["Delivery"])
