from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.letter import LetterCreate, LetterUpdate, LetterResponse, LetterListResponse
from app.services.letter_service import LetterService

router = APIRouter()


@router.post("/", response_model=LetterResponse, status_code=status.HTTP_201_CREATED, summary="Create a new love/birthday letter")
async def create_letter(
    data: LetterCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new letter with personal details, text content, photos, music track, and delivery options.
    Generates a unique access slug (e.g., `love-a8x92k`).
    """
    return await LetterService.create_letter(db, data)


@router.get("/", response_model=LetterListResponse, summary="List all letters")
async def list_letters(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None, description="Filter by letter type ('love' or 'birthday')"),
    db: AsyncSession = Depends(get_db)
):
    letters, total = await LetterService.list_letters(db, skip=skip, limit=limit, type_filter=type)
    return LetterListResponse(total=total, letters=letters)


@router.get("/{slug}", response_model=LetterResponse, summary="Get letter by slug")
async def get_letter_by_slug(
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


@router.put("/{slug}", response_model=LetterResponse, summary="Update letter details")
async def update_letter(
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


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete letter")
async def delete_letter(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    deleted = await LetterService.delete_letter(db, slug)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Letter with slug '{slug}' not found"
        )
    return None
