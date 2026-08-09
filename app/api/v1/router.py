from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.delivery.router import router as delivery_router
from app.modules.health.router import router as health_router
from app.modules.letters.router import (
    birthday_invite_router,
    birthday_router,
    generic_router as letters_router,
    love_router,
    valentine_router,
    wedding_router,
)
from app.modules.media.router import router as media_router
from app.modules.music.router import router as music_router
from app.modules.templates.router import router as templates_router

from app.modules.admin.router import router as admin_router
from app.modules.payments.router import router as payments_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["Health"])
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])

# One route group per letter type.
api_router.include_router(love_router, prefix="/love-letters", tags=["Love Letters"])
api_router.include_router(valentine_router, prefix="/valentine-letters", tags=["Valentine Letters"])
api_router.include_router(birthday_router, prefix="/birthday-letters", tags=["Birthday Letters"])
api_router.include_router(birthday_invite_router, prefix="/birthday-invitations", tags=["Birthday Invitations"])
api_router.include_router(wedding_router, prefix="/wedding-invitations", tags=["Wedding Invitations"])

api_router.include_router(letters_router, prefix="/letters", tags=["Letters (generic)"])
api_router.include_router(payments_router, prefix="/payments", tags=["Payments"])
api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
api_router.include_router(templates_router, prefix="/templates", tags=["Templates"])
api_router.include_router(music_router, prefix="/music", tags=["Music"])
api_router.include_router(media_router, prefix="/media", tags=["Media"])
api_router.include_router(delivery_router, prefix="/delivery", tags=["Delivery"])
