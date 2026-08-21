import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import hash_password, sign_purpose_token, verify_password
from app.core.database import get_db
from app.core.deps import require_admin, current_user
from app.modules.auth.models import User
from app.modules.auth.service import AuthService
from app.modules.delivery.email_service import EmailService
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

logger = logging.getLogger(__name__)
router = APIRouter()


def _percent_delta(current: float, previous: float) -> str:
    """Period-over-period change. With no prior activity a percentage is
    meaningless (any growth is "infinite"), so say "new" instead of inventing
    a number."""
    if previous == 0:
        return "new" if current else "—"
    change = (current - previous) / previous * 100
    return f"{change:+.1f}%"


def _count_delta(current: int, previous: int) -> str:
    return f"{current - previous:+d}"


async def _count_between(
    db: AsyncSession, model, column, start: datetime, end: Optional[datetime] = None
) -> int:
    query = select(func.count()).select_from(model).where(column >= start)
    if end is not None:
        query = query.where(column < end)
    return (await db.execute(query)).scalar_one() or 0


@router.get("/stats", response_model=List[StatItem])
async def get_admin_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    now = datetime.now(timezone.utc)
    last_30 = now - timedelta(days=30)
    prior_30 = now - timedelta(days=60)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    yesterday_start = today_start - timedelta(days=1)

    total_users = (await db.execute(select(func.count(User.id)))).scalar_one() or 0
    total_letters = (await db.execute(select(func.count(Letter.id)))).scalar_one() or 0

    users_recent = await _count_between(db, User, User.created_at, last_30)
    users_prior = await _count_between(db, User, User.created_at, prior_30, last_30)
    letters_recent = await _count_between(db, Letter, Letter.created_at, last_30)
    letters_prior = await _count_between(db, Letter, Letter.created_at, prior_30, last_30)

    async def revenue_between(start: datetime, end: Optional[datetime] = None) -> float:
        query = select(func.sum(Payment.amount)).where(
            Payment.status == "Paid", Payment.created_at >= start
        )
        if end is not None:
            query = query.where(Payment.created_at < end)
        return float((await db.execute(query)).scalar_one_or_none() or 0.0)

    revenue_recent = await revenue_between(last_30)
    revenue_prior = await revenue_between(prior_30, last_30)

    delivered_today = await _count_between(db, Letter, Letter.created_at, today_start)
    delivered_yesterday = await _count_between(db, Letter, Letter.created_at, yesterday_start, today_start)

    return [
        StatItem(label="Total users", value=f"{total_users:,}", delta=_percent_delta(users_recent, users_prior)),
        StatItem(
            label="Letters created",
            value=f"{total_letters:,}",
            delta=_percent_delta(letters_recent, letters_prior),
        ),
        StatItem(
            label="Revenue (30d)",
            value=f"${revenue_recent:,.2f}",
            delta=_percent_delta(revenue_recent, revenue_prior),
        ),
        StatItem(
            label="Delivered today",
            value=str(delivered_today),
            delta=_count_delta(delivered_today, delivered_yesterday),
        ),
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
    # get_by_email, not a bare ==: emails are case-insensitive, and only
    # Postgres has CITEXT to enforce that at the column.
    if await AuthService.get_by_email(db, body.email):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User with this email already exists.")

    invited = User(
        name=body.email.split("@")[0].capitalize(),
        email=body.email.strip().lower(),
        role="user",
    )
    db.add(invited)
    await db.commit()
    await db.refresh(invited)

    # No password_hash, so the account cannot be signed into until they set one.
    # The invite is a reset-password link, valid for a week.
    token = sign_purpose_token("reset-password", str(invited.id), minutes=7 * 24 * 60)
    link = f"{settings.PUBLIC_APP_URL.rstrip('/')}/reset-password?token={token}"
    sent = await EmailService.send_invite(invited.email, link) if settings.smtp_enabled else False
    if not sent:
        logger.warning("Could not email invite to %s -- link: %s", invited.email, link)

    message = (
        f"Invitation sent to {invited.email}"
        if sent
        else f"Account created for {invited.email}, but the invitation email could not be sent."
    )
    return {"message": message, "id": f"USR-{invited.id + 1000}", "email_sent": sent}


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
async def delete_admin_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    cleaned = user_id.strip()
    target_id = None
    if cleaned.upper().startswith("USR-"):
        try:
            target_id = int(cleaned[4:]) - 1000
        except ValueError:
            pass
    if target_id is None:
        try:
            target_id = int(cleaned)
        except ValueError:
            pass

    if target_id is None or target_id <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid user ID format: {user_id}")

    res = await db.execute(select(User).where(User.id == target_id))
    target_user = res.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User '{user_id}' not found.")

    if target_user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot delete your own admin account.")

    user_name = target_user.name
    user_email = target_user.email
    await db.delete(target_user)
    await db.commit()

    return {"message": f"User '{user_name}' ({user_email}) has been deleted successfully.", "ok": True}


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
    pending_count = 0
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
        elif payment.status == "Pending":
            pending_count += 1

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

    avg_order = (total_rev / paid_count) if paid_count > 0 else 0.0

    stats = [
        StatItem(
            label="Revenue (all time)",
            value=f"${total_rev:,.2f}",
            delta=f"{paid_count} paid" if paid_count else "no payments yet",
        ),
        StatItem(label="Transactions", value=f"{len(items):,}", delta=f"{pending_count} pending"),
        StatItem(label="Refunds", value=f"${refunded_sum:,.2f}", delta=f"{refunded_count} total"),
        StatItem(
            label="Avg. order",
            value=f"${avg_order:,.2f}",
            delta="across paid orders" if paid_count else "—",
        ),
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
