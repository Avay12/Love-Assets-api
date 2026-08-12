from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    payment_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    letter_id: Mapped[Optional[int]] = mapped_column(ForeignKey("letters.id", ondelete="SET NULL"), nullable=True, index=True)

    amount: Mapped[float] = mapped_column(Float, default=4.99, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)

    payment_method: Mapped[str] = mapped_column(String(32), default="Card", nullable=False)
    # Pending -> Paid | Refunded. Nothing moves an order to Paid yet: there is
    # no payment gateway wired up.
    status: Mapped[str] = mapped_column(String(32), default="Pending", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", backref="payments")
    letter = relationship("Letter", backref="payments")
