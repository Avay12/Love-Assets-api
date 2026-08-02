from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

LETTER_TYPES = ("love", "valentine", "birthday", "birthday-invite", "wedding")


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


class LetterCommon(BaseModel):
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


class LoveDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ValentineDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rsvp_enabled: bool = True
    date_night: Optional[str] = Field(default=None, max_length=200)


def turning_age_from(birth_date: Optional[date], event_date: Optional[date]) -> Optional[int]:
    if not birth_date:
        return None
    on = event_date or date.today()
    return on.year - birth_date.year - ((on.month, on.day) < (birth_date.month, birth_date.day))


class _CelebrantMixin(BaseModel):
    celebrant_name: Optional[str] = Field(default=None, max_length=128)
    birth_date: Optional[date] = None
    age: Optional[str] = Field(
        default=None, max_length=8, description="Free-text age, used when no birth_date is given"
    )
    turning_age: Optional[int] = Field(default=None, description="Server-derived; any client value is discarded")

    @model_validator(mode="after")
    def _derive_turning_age(self):
        event_on = getattr(self, "event_at", None)
        derived = turning_age_from(self.birth_date, event_on.date() if event_on else None)
        object.__setattr__(self, "turning_age", derived)
        if derived is not None and not self.age:
            object.__setattr__(self, "age", str(derived))
        return self


class BirthdayDetails(_CelebrantMixin):
    model_config = ConfigDict(extra="forbid")


class BirthdayInviteDetails(_CelebrantMixin):
    model_config = ConfigDict(extra="forbid")

    event_at: Optional[datetime] = Field(
        default=None, description="Party start. Send with an explicit UTC offset."
    )
    date_line: Optional[str] = Field(default=None, max_length=120, description="e.g. 'Saturday, 8 August 2026'")
    time_line: Optional[str] = Field(default=None, max_length=60, description="e.g. '17.00 WIB'")
    venue: Optional[Venue] = None

    attendance_manager: Optional[str] = Field(default=None, max_length=128)
    attendance_manager_contact: Optional[str] = Field(default=None, max_length=128)

    rsvp_enabled: bool = True
    rsvp_deadline: Optional[date] = None

    dress_code: Optional[str] = Field(default=None, max_length=200)
    quote: Optional[str] = Field(default=None, max_length=600)
    quote_author: Optional[str] = Field(default=None, max_length=120)
    story: Optional[str] = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def _rsvp_deadline_before_event(self):
        if self.rsvp_deadline and self.event_at and self.rsvp_deadline > self.event_at.date():
            raise ValueError("rsvp_deadline must be on or before the event date")
        return self


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


class TypedLetterResponse(LetterCommon):
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
