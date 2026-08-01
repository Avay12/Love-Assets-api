"""One router per letter type.

Each type gets its own path, its own request model and its own OpenAPI entry,
so `/docs` documents exactly what a wedding invitation accepts versus a
birthday letter. They are built from a single factory so the five stay
identical in behaviour and only differ where they should: the payload schema.
"""

from typing import Type

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.letter_types import (
    BirthdayInviteCreate,
    BirthdayLetterCreate,
    LetterCommon,
    LoveLetterCreate,
    TypedLetterListResponse,
    TypedLetterResponse,
    ValentineLetterCreate,
    WeddingInviteCreate,
)
from app.services.typed_letter_service import TypedLetterService


def build_router(letter_type: str, create_model: Type[LetterCommon], label: str) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/",
        response_model=TypedLetterResponse,
        status_code=status.HTTP_201_CREATED,
        summary=f"Create a {label}",
    )
    async def create(data: create_model, db: AsyncSession = Depends(get_db)):  # type: ignore[valid-type]
        """Creates the letter and returns its slug plus the public share URL."""
        return await TypedLetterService.create(db, letter_type, data)

    @router.get("/", response_model=TypedLetterListResponse, summary=f"List {label}s")
    async def list_all(
        skip: int = Query(0, ge=0),
        limit: int = Query(20, ge=1, le=100),
        db: AsyncSession = Depends(get_db),
    ):
        letters, total = await TypedLetterService.list_by_type(db, letter_type, skip=skip, limit=limit)
        return TypedLetterListResponse(total=total, letters=letters)

    @router.get("/{slug}", response_model=TypedLetterResponse, summary=f"Get a {label} by slug")
    async def get_one(slug: str, db: AsyncSession = Depends(get_db)):
        letter = await TypedLetterService.get_by_slug(db, slug)
        if not letter or letter.type != letter_type:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"No {label} with slug '{slug}'")
        return letter

    @router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT, summary=f"Delete a {label}")
    async def remove(slug: str, db: AsyncSession = Depends(get_db)):
        if not await TypedLetterService.delete_by_slug(db, slug, letter_type):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"No {label} with slug '{slug}'")
        return None

    return router


love_router = build_router("love", LoveLetterCreate, "love letter")
valentine_router = build_router("valentine", ValentineLetterCreate, "valentine letter")
birthday_router = build_router("birthday", BirthdayLetterCreate, "birthday letter")
birthday_invite_router = build_router("birthday-invite", BirthdayInviteCreate, "birthday invitation")
wedding_router = build_router("wedding", WeddingInviteCreate, "wedding invitation")
