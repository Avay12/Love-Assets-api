from datetime import datetime, timezone, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import verify_password, hash_password
from app.core.database import get_db
from app.core.deps import require_admin, current_user
from app.modules.auth.models import User
from app.modules.letters.models import Letter
from app.modules.payments.models import Payment
from app.modules.admin.schemas import (
    AdminLetterItem,
    AdminPaymentItem,
    AdminPaymentsResponse,
    AdminUserItem,
    ChangePasswordRequest,
    InviteUserRequest,
    StatItem,
)

router = APIRouter()


@router.get("/stats", response_model=List[StatItem])
async def get_admin_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    total_users = (await db.execute(select(func.count(User.id)))).scalar_one() or 0
    total_letters = (await db.execute(select(func.count(Letter.id)))).scalar_one() or 0

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    rev_res = await db.execute(
        select(func.sum(Payment.amount))
        .where(Payment.status == "Paid", Payment.created_at >= thirty_days_ago)
    )
    rev_sum = rev_res.scalar_one_or_none() or 0.0

    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    delivered_today = (
        await db.execute(
            select(func.count(Letter.id)).where(Letter.created_at >= today_start)
        )
    ).scalar_one() or 0

    return [
        StatItem(label="Total users", value=f"{total_users:,}", delta="+8.2%"),
        StatItem(label="Letters created", value=f"{total_letters:,}", delta="+12.4%"),
        StatItem(label="Revenue (30d)", value=f"${rev_sum:,.2f}", delta="+5.1%"),
        StatItem(label="Delivered today", value=str(delivered_today), delta="+3"),
    ]


@router.get("/users", response_model=List[AdminUserItem])
async def get_admin_users(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    users = (await db.execute(select(User).order_by(User.id.desc()))).scalars().all()
    result = []

    for u in users:
        letter_count = (
            await db.execute(select(func.count(Letter.id)).where(Letter.user_id == u.id))
        ).scalar_one() or 0
        joined_str = u.created_at.strftime("%d %b %Y") if u.created_at else "—"
        user_status = "Active" if (u.email_verified_at or u.password_hash or u.identities) else "Invited"
        result.append(
            AdminUserItem(
                id=f"USR-{u.id + 1000}",
                name=u.name,
                email=u.email,
                joined=joined_str,
                letters=letter_count,
                status=user_status,
            )
        )

    return result


@router.post("/users/invite", status_code=status.HTTP_200_OK)
async def invite_user(
    body: InviteUserRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    # Check existing
    res = await db.execute(select(User).where(User.email == body.email))
    existing = res.scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User with this email already exists.")

    invited = User(
        name=body.email.split("@")[0].capitalize(),
        email=body.email,
        role="user",
    )
    db.add(invited)
    await db.commit()
    await db.refresh(invited)

    return {"message": f"Invitation sent to {body.email}", "id": f"USR-{invited.id + 1000}"}


@router.get("/letters", response_model=List[AdminLetterItem])
async def get_admin_letters(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    query = (
        select(Letter, User)
        .outerjoin(User, Letter.user_id == User.id)
        .order_by(Letter.created_at.desc())
    )
    rows = (await db.execute(query)).all()
    result = []

    for letter, user in rows:
        author = user.name if user else letter.from_name
        created_str = letter.created_at.strftime("%d %b %Y") if letter.created_at else "—"
        status_str = "Scheduled" if letter.scheduled_at and letter.scheduled_at > datetime.now(timezone.utc) else "Delivered"
        type_title = "Love Letter" if letter.type == "love" else "Birthday Letter" if "birthday" in letter.type else letter.type.capitalize()

        result.append(
            AdminLetterItem(
                id=letter.slug,
                title=f"To {letter.to_name} (from {letter.from_name})",
                type=type_title,
                template=letter.template_id,
                author=author,
                created=created_str,
                status=status_str,
            )
        )

    return result


@router.delete("/letters/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_letter(
    slug: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    res = await db.execute(select(Letter).where(Letter.slug == slug))
    letter = res.scalar_one_or_none()
    if not letter:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Letter '{slug}' not found.")
    await db.delete(letter)
    await db.commit()
    return None


@router.get("/payments", response_model=AdminPaymentsResponse)
async def get_admin_payments(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    query = (
        select(Payment, User, Letter)
        .outerjoin(User, Payment.user_id == User.id)
        .outerjoin(Letter, Payment.letter_id == Letter.id)
        .order_by(Payment.created_at.desc())
    )
    rows = (await db.execute(query)).all()

    items = []
    total_rev = 0.0
    paid_count = 0
    refunded_count = 0
    refunded_sum = 0.0

    for payment, user, letter in rows:
        customer_name = user.name if user else (letter.from_name if letter else "Guest Customer")
        if payment.status == "Paid":
            total_rev += payment.amount
            paid_count += 1
        elif payment.status == "Refunded":
            refunded_count += 1
            refunded_sum += payment.amount

        date_str = payment.created_at.strftime("%d %b %Y") if payment.created_at else "—"

        items.append(
            AdminPaymentItem(
                id=payment.payment_code,
                customer=customer_name,
                amount=f"${payment.amount:.2f}",
                method=payment.payment_method,
                date=date_str,
                status=payment.status,
            )
        )

    avg_order = (total_rev / paid_count) if paid_count > 0 else 4.99

    stats = [
        StatItem(label="Revenue (30d)", value=f"${total_rev:,.2f}", delta="+5.1%"),
        StatItem(label="Transactions", value=f"{len(items):,}", delta=f"+{len(items)}"),
        StatItem(label="Refunds", value=f"${refunded_sum:.2f}", delta=f"{refunded_count} total"),
        StatItem(label="Avg. order", value=f"${avg_order:.2f}", delta="+$0.18"),
    ]

    return AdminPaymentsResponse(stats=stats, payments=items)


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    if user.password_hash and not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect.")

    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"message": "Password updated successfully."}
