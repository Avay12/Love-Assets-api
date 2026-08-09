from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr


class StatItem(BaseModel):
    label: str
    value: str
    delta: str


class AdminUserItem(BaseModel):
    id: str
    name: str
    email: str
    joined: str
    letters: int
    status: str


class AdminLetterItem(BaseModel):
    id: str
    title: str
    type: str
    template: str
    author: str
    created: str
    status: str


class AdminPaymentItem(BaseModel):
    id: str
    customer: str
    amount: str
    method: str
    date: str
    status: str


class AdminPaymentsResponse(BaseModel):
    stats: List[StatItem]
    payments: List[AdminPaymentItem]


class InviteUserRequest(BaseModel):
    email: EmailStr


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
