from typing import List, Optional
from fastapi import APIRouter, Query

from app.modules.music.schemas import TrackResult, MusicSearchResponse
from app.modules.music.service import MusicService

router = APIRouter()


@router.get("/featured", response_model=List[TrackResult], summary="Get featured songs")
async def get_featured_songs():
    return MusicService.get_featured_songs()


@router.get("/search", response_model=MusicSearchResponse, summary="Search music tracks")
async def search_music(
    q: Optional[str] = Query("", description="Search term for song title or artist")
):
    query_str = q or ""
    results = MusicService.search_songs(query_str)
    return MusicSearchResponse(query=query_str, results=results)
