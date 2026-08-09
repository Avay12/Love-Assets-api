from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import current_user, current_user_optional
from app.modules.auth.models import User
from app.modules.letters.models import Letter
from app.modules.letters.schemas import (
    BirthdayInviteCreate,
    BirthdayLetterCreate,
    LetterCreate,
    LetterListResponse,
    LetterResponse,
    LetterUpdate,
    LoveLetterCreate,
    TypedLetterListResponse,
    TypedLetterResponse,
    ValentineLetterCreate,
    WeddingInviteCreate,
)
from app.modules.letters.service import LetterService, TypedLetterService

router = APIRouter()

# --------------------------------------------------------------------------
# Type-specific routers for frontend experience endpoints
# --------------------------------------------------------------------------


def _make_type_router(letter_type: str, create_schema) -> APIRouter:
    r = APIRouter()

    @r.post("", response_model=TypedLetterResponse, status_code=status.HTTP_201_CREATED)
    @r.post("/", response_model=TypedLetterResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
    async def create(
        data: create_schema,
        db: AsyncSession = Depends(get_db),
        user: Optional[User] = Depends(current_user_optional),
    ):
        return await TypedLetterService.create(db, letter_type, data, user_id=user.id if user else None)

    @r.get("", response_model=TypedLetterListResponse)
    @r.get("/", response_model=TypedLetterListResponse, include_in_schema=False)
    async def list_items(
        skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db)
    ):
        letters, total = await TypedLetterService.list_by_type(db, letter_type, skip=skip, limit=limit)
        return TypedLetterListResponse(total=total, letters=letters)

    @r.get("/{slug}", response_model=TypedLetterResponse)
    async def get_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
        res = await TypedLetterService.get_by_slug(db, slug, letter_type)
        if not res:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Letter '{slug}' not found.")
        return res

    @r.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
        if not await TypedLetterService.delete_by_slug(db, slug, letter_type):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Letter '{slug}' not found.")
        return None

    return r


love_router = _make_type_router("love", LoveLetterCreate)
valentine_router = _make_type_router("valentine", ValentineLetterCreate)
birthday_router = _make_type_router("birthday", BirthdayLetterCreate)
birthday_invite_router = _make_type_router("birthday-invite", BirthdayInviteCreate)
wedding_router = _make_type_router("wedding", WeddingInviteCreate)


# --------------------------------------------------------------------------
# Generic /letters endpoint router
# --------------------------------------------------------------------------

generic_router = APIRouter()


@generic_router.get("/my-letters", summary="List authenticated user's letters")
async def list_my_letters(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    query = select(Letter).where(Letter.user_id == user.id).order_by(Letter.created_at.desc())
    letters = (await db.execute(query)).scalars().all()

    items = []
    for l in letters:
        status_str = "Scheduled" if l.scheduled_at and l.scheduled_at > datetime.now(timezone.utc) else "Delivered"
        song_str = f"{l.song_title} — {l.song_artist}" if l.song_title else None
        date_str = l.created_at.strftime("%d %b %Y") if l.created_at else "Today"
        type_str = "Love Letter" if l.type == "love" else "Birthday Letter" if "birthday" in l.type else l.type.capitalize()
        items.append({
            "id": l.slug,
            "title": f"Letter for {l.to_name}",
            "recipient": l.to_name,
            "type": type_str,
            "template": l.template_id,
            "song": song_str,
            "delivery": l.delivery_method.capitalize(),
            "created": date_str,
            "status": status_str,
        })
    return {"total": len(items), "letters": items}


@generic_router.post("", response_model=LetterResponse, status_code=status.HTTP_201_CREATED, summary="Create a generic letter")
@generic_router.post("/", response_model=LetterResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_generic_letter(
    data: LetterCreate,
    db: AsyncSession = Depends(get_db)
):
    return await LetterService.create_letter(db, data)


@generic_router.get("", response_model=LetterListResponse, summary="List all letters")
@generic_router.get("/", response_model=LetterListResponse, include_in_schema=False)
async def list_generic_letters(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    type: str = Query(None, description="Filter by letter type"),
    db: AsyncSession = Depends(get_db)
):
    letters, total = await LetterService.list_letters(db, skip=skip, limit=limit, type_filter=type)
    return LetterListResponse(total=total, letters=letters)


@generic_router.get("/{slug}", response_model=LetterResponse, summary="Get a letter by slug")
async def get_generic_letter(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    letter = await LetterService.get_letter_by_slug(db, slug)
    if not letter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Letter with slug '{slug}' not found"
        )
    return letter


@generic_router.put("/{slug}", response_model=LetterResponse, summary="Update a letter")
async def update_generic_letter(
    slug: str,
    data: LetterUpdate,
    db: AsyncSession = Depends(get_db)
):
    letter = await LetterService.update_letter(db, slug, data)
    if not letter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Letter with slug '{slug}' not found"
        )
    return letter


@generic_router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a letter")
async def delete_generic_letter(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    success = await LetterService.delete_letter(db, slug)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Letter with slug '{slug}' not found"
        )
    return None
