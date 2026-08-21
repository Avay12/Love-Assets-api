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



class DeliveryPricing(BaseModel):
    link: float = Field(default=1.0, ge=0.0, description="Price for Private Link delivery in USD")
    email: float = Field(default=2.0, ge=0.0, description="Price for Email delivery in USD")
    sms: float = Field(default=3.0, ge=0.0, description="Price for SMS delivery in USD")
    call: float = Field(default=4.0, ge=0.0, description="Price for Voice Call delivery in USD")
