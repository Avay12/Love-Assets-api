from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    health,
    letter_types,
    letters,
    templates,
    music,
    media,
    delivery,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])

# One route group per letter type. These are what the frontend uses; the
# generic /letters group below stays for cross-type listing and admin.
api_router.include_router(letter_types.love_router, prefix="/love-letters", tags=["Love Letters"])
api_router.include_router(letter_types.valentine_router, prefix="/valentine-letters", tags=["Valentine Letters"])
api_router.include_router(letter_types.birthday_router, prefix="/birthday-letters", tags=["Birthday Letters"])
api_router.include_router(
    letter_types.birthday_invite_router, prefix="/birthday-invitations", tags=["Birthday Invitations"]
)
api_router.include_router(letter_types.wedding_router, prefix="/wedding-invitations", tags=["Wedding Invitations"])

api_router.include_router(letters.router, prefix="/letters", tags=["Letters (generic)"])
api_router.include_router(templates.router, prefix="/templates", tags=["Templates"])
api_router.include_router(music.router, prefix="/music", tags=["Music"])
api_router.include_router(media.router, prefix="/media", tags=["Media"])
api_router.include_router(delivery.router, prefix="/delivery", tags=["Delivery"])
