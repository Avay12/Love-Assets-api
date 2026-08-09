from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import current_user
from app.modules.auth.models import User
from app.modules.letters.models import Letter
from app.modules.payments.models import Payment
from app.modules.payments.schemas import MyPaymentResponse, PaymentListResponse

router = APIRouter()


@router.get("/my-payments", response_model=PaymentListResponse)
async def get_my_payments(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    query = (
        select(Payment, Letter)
        .outerjoin(Letter, Payment.letter_id == Letter.id)
        .where(Payment.user_id == user.id)
        .order_by(Payment.created_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()

    items = []
    total_paid = 0.0

    for payment, letter in rows:
        amount_str = f"${payment.amount:.2f}"
        if payment.status == "Paid":
            total_paid += payment.amount

        date_str = payment.created_at.strftime("%d %b %Y") if payment.created_at else "Today"

        items.append(
            MyPaymentResponse(
                id=payment.payment_code,
                amount=amount_str,
                method=payment.payment_method,
                date=date_str,
                status=payment.status,
                letterId=letter.slug if letter else f"LTR-{payment.letter_id or payment.id}",
                letterTitle=f"Letter for {letter.to_name}" if letter else "Keepsake Letter",
                letterType=letter.type if letter else "Love Letter",
                letterTemplate=letter.template_id if letter else "Standard",
            )
        )

    return PaymentListResponse(total=len(items), total_paid=total_paid, payments=items)
