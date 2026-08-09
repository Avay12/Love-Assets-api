from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class MyPaymentResponse(BaseModel):
    id: str
    amount: str
    method: str
    date: str
    status: str
    letterId: str
    letterTitle: Optional[str] = None
    letterType: Optional[str] = None
    letterTemplate: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaymentListResponse(BaseModel):
    total: int
    total_paid: float
    payments: List[MyPaymentResponse]
