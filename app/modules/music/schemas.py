from typing import List, Optional
from pydantic import BaseModel


class TrackResult(BaseModel):
    id: str
    title: str
    artist: str
    preview_url: Optional[str] = None
    cover_url: Optional[str] = None


class MusicSearchResponse(BaseModel):
    query: str
    results: List[TrackResult]
