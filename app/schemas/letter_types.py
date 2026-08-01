"""Per-type request/response schemas.

Every letter type shares the same storage row (see ``app.db.models.letter``);
what differs is the ``details`` payload. Each type below declares its own
details model so FastAPI validates and documents the right shape per endpoint,
instead of accepting a free-form blob everywhere.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# Canonical type slugs. These match the frontend's create-letter TYPES ids.
LETTER_TYPES = ("love", "valentine", "birthday", "birthday-invite", "wedding")


# --------------------------------------------------------------------------
# shared pieces
# --------------------------------------------------------------------------


class LetterCommon(BaseModel):
    """Fields every letter type accepts."""

    template_id: str = Field(default="mailbox", max_length=64)
    from_name: str = Field(..., min_length=1, max_length=128)
    to_name: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=5000)
    photos: List[str] = Field(default_factory=list, max_length=12)

    song_id: Optional[str] = Field(default=None, max_length=128)
    song_title: Optional[str] = Field(default=None, max_length=256)
    song_artist: Optional[str] = Field(default=None, max_length=256)
    song_preview_url: Optional[str] = Field(default=None, max_length=512)
    artwork: Optional[str] = Field(default=None, max_length=512)

    delivery_method: Literal["link", "email", "sms", "call"] = "link"
    delivery_contact: Optional[str] = Field(default=None, max_length=256)
    scheduled_at: Optional[datetime] = None


class Venue(BaseModel):
    name: str = Field(..., max_length=160)
    address: List[str] = Field(default_factory=list, max_length=6)
    maps_url: Optional[str] = Field(default=None, max_length=512)


class BankAccount(BaseModel):
    bank: str = Field(..., max_length=64)
    number: str = Field(..., max_length=64)
    holder: str = Field(..., max_length=128)


class StoryChapter(BaseModel):
    title: str = Field(..., max_length=160)
    body: str = Field(..., max_length=2000)


# --------------------------------------------------------------------------
# per-type details
# --------------------------------------------------------------------------


class LoveDetails(BaseModel):
    """Love letters carry no extra data beyond the shared fields."""

    model_config = ConfigDict(extra="forbid")


class ValentineDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rsvp_enabled: bool = True
    date_night: Optional[str] = Field(default=None, max_length=200)


class BirthdayDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age: Optional[str] = Field(default=None, max_length=8)


class BirthdayInviteDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age: Optional[str] = Field(default=None, max_length=8)
    event_at: Optional[datetime] = Field(
        default=None, description="Party start. Send with an explicit UTC offset."
    )
    date_line: Optional[str] = Field(default=None, max_length=120, description="e.g. 'Saturday, 8 August 2026'")
    time_line: Optional[str] = Field(default=None, max_length=60, description="e.g. '17.00 WIB'")
    venue: Optional[Venue] = None
    quote: Optional[str] = Field(default=None, max_length=600)
    quote_author: Optional[str] = Field(default=None, max_length=120)
    story: Optional[str] = Field(default=None, max_length=4000)


class WeddingDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bride_parents: Optional[str] = Field(default=None, max_length=200)
    groom_parents: Optional[str] = Field(default=None, max_length=200)
    event_at: Optional[datetime] = Field(
        default=None, description="Ceremony start. Send with an explicit UTC offset."
    )
    date_line: Optional[str] = Field(default=None, max_length=120)
    akad_time: Optional[str] = Field(default=None, max_length=60)
    reception_time: Optional[str] = Field(default=None, max_length=60)
    venue: Optional[Venue] = None
    dress_code: Optional[str] = Field(default=None, max_length=200)
    gift_accounts: List[BankAccount] = Field(default_factory=list, max_length=4)
    story: List[StoryChapter] = Field(default_factory=list, max_length=6)


# --------------------------------------------------------------------------
# per-type create payloads
# --------------------------------------------------------------------------


class LoveLetterCreate(LetterCommon):
    details: LoveDetails = Field(default_factory=LoveDetails)


class ValentineLetterCreate(LetterCommon):
    details: ValentineDetails = Field(default_factory=ValentineDetails)


class BirthdayLetterCreate(LetterCommon):
    details: BirthdayDetails = Field(default_factory=BirthdayDetails)


class BirthdayInviteCreate(LetterCommon):
    details: BirthdayInviteDetails = Field(default_factory=BirthdayInviteDetails)


class WeddingInviteCreate(LetterCommon):
    details: WeddingDetails = Field(default_factory=WeddingDetails)


# --------------------------------------------------------------------------
# response
# --------------------------------------------------------------------------


class TypedLetterResponse(LetterCommon):
    """One response shape for every type; ``details`` holds the type payload."""

    id: int
    slug: str
    type: str
    share_url: str = Field(..., description="Public URL the recipient opens")
    details: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TypedLetterListResponse(BaseModel):
    total: int
    letters: List[TypedLetterResponse]
