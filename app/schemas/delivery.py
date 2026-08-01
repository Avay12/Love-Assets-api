from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DeliveryRequest(BaseModel):
    letter_slug: str = Field(..., description="Slug of the letter to deliver")
    method: str = Field(..., description="Delivery method: link, email, sms, call")
    contact: Optional[str] = Field(None, description="Recipient email address or phone number")
    scheduled_at: Optional[datetime] = Field(None, description="Optional scheduled dispatch datetime")


class DeliveryResponse(BaseModel):
    success: bool
    message: str
    letter_slug: str
    method: str
    contact: Optional[str] = None
    scheduled_at: Optional[datetime] = None
