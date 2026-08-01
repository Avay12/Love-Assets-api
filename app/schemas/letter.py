from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MusicTrackInfo(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    artist: Optional[str] = None
    preview_url: Optional[str] = None


class LetterBase(BaseModel):
    type: str = Field(default="love", description="Type of letter: 'love' or 'birthday'")
    template_id: str = Field(default="mailbox", description="Template identifier")
    from_name: str = Field(..., min_length=1, max_length=128, description="Sender name")
    to_name: str = Field(..., min_length=1, max_length=128, description="Recipient name")
    message: str = Field(..., min_length=1, max_length=5000, description="Letter content")
    photos: List[str] = Field(default_factory=list, description="List of image URLs/paths")
    song_id: Optional[str] = None
    song_title: Optional[str] = None
    song_artist: Optional[str] = None
    song_preview_url: Optional[str] = None
    delivery_method: str = Field(default="link", description="Delivery method: link, email, sms, call")
    delivery_contact: Optional[str] = Field(default=None, description="Target email or phone number")
    scheduled_at: Optional[datetime] = None


class LetterCreate(LetterBase):
    pass


class LetterUpdate(BaseModel):
    from_name: Optional[str] = None
    to_name: Optional[str] = None
    message: Optional[str] = None
    template_id: Optional[str] = None
    photos: Optional[List[str]] = None
    song_id: Optional[str] = None
    song_title: Optional[str] = None
    song_artist: Optional[str] = None
    song_preview_url: Optional[str] = None
    delivery_method: Optional[str] = None
    delivery_contact: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class LetterResponse(LetterBase):
    id: int
    slug: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LetterListResponse(BaseModel):
    total: int
    letters: List[LetterResponse]
