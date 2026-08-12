from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class DeliveryRequest(BaseModel):
    letter_slug: str = Field(..., description="Slug of the letter to deliver")
    method: Literal["link", "email", "sms", "call"] = Field(..., description="Delivery method")
    contact: Optional[str] = Field(None, description="Recipient email address or phone number")
    scheduled_at: Optional[datetime] = Field(None, description="Optional scheduled dispatch datetime")


class DeliveryResponse(BaseModel):
    success: bool
    message: str
    letter_slug: str
    method: str
    contact: Optional[str] = None
    scheduled_at: Optional[datetime] = None
