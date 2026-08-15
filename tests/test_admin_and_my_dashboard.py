import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import hash_password
from app.core.deps import ACCESS_COOKIE, reset_rate_limits
from app.modules.auth.models import User


@pytest.fixture(autouse=True)
def _clear_limits():
    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.mark.asyncio
async def test_my_letters_and_payments_flow(client: AsyncClient, db_session: AsyncSession):
    # 1. Register a test user
    reg = await client.post(
        "/api/v1/auth/register",
        json={"name": "Sarah Connor", "email": "sarah@example.com", "password": "Password123!"},
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]
    client.cookies.set(ACCESS_COOKIE, token)

    # 2. Create a letter while authenticated
    letter_res = await client.post(
        "/api/v1/love-letters/",
        json={
            "template_id": "mailbox",
            "from_name": "Sarah",
            "to_name": "Kyle",
            "message": "Come with me if you want to live.",
            "photos": [],
            "delivery_method": "link",
            "details": {},
        },
    )
    assert letter_res.status_code == 201, letter_res.text

    # 3. Fetch my letters
    my_letters_res = await client.get("/api/v1/letters/my-letters")
    assert my_letters_res.status_code == 200, my_letters_res.text
    letters_data = my_letters_res.json()
    assert letters_data["total"] >= 1
    assert letters_data["letters"][0]["recipient"] == "Kyle"

    # 4. Fetch my payments
    my_pay_res = await client.get("/api/v1/payments/my-payments")
    assert my_pay_res.status_code == 200, my_pay_res.text
    pay_data = my_pay_res.json()
    assert pay_data["total"] >= 1
    # The order is recorded, but nothing has taken any money: no payment
    # gateway is wired up, so it opens Pending and total_paid stays at zero.
    assert pay_data["payments"][0]["status"] == "Pending"
    assert pay_data["total_paid"] == 0.0


@pytest.mark.asyncio
async def test_admin_dashboard_protection_and_stats(client: AsyncClient, db_session: AsyncSession):
    # 1. Register user & upgrade role to admin in DB
    reg = await client.post(
        "/api/v1/auth/register",
        json={"name": "Admin Boss", "email": "boss@wish2luv.com", "password": "AdminPass123!"},
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]
    user_id = reg.json()["user"]["id"]

    client.cookies.set(ACCESS_COOKIE, token)

    admin_user = await db_session.get(User, user_id)
    assert admin_user is not None
    admin_user.role = "admin"
    await db_session.commit()

    # 2. Authenticated admin calls stats
    stats_res = await client.get("/api/v1/admin/stats")
    assert stats_res.status_code == 200, stats_res.text
    stats_data = stats_res.json()
    assert len(stats_data) == 4
    labels = [s["label"] for s in stats_data]
    assert "Total users" in labels
    assert "Revenue (30d)" in labels

    # 3. Admin calls users list
    users_res = await client.get("/api/v1/admin/users")
    assert users_res.status_code == 200, users_res.text
    assert len(users_res.json()) >= 1

    # 4. Admin invites a new user
    invite_res = await client.post("/api/v1/admin/users/invite", json={"email": "invited@example.com"})
    assert invite_res.status_code == 200, invite_res.text

    # 5. Admin calls letters list
    letters_res = await client.get("/api/v1/admin/letters")
    assert letters_res.status_code == 200, letters_res.text

    # 6. Admin calls payments list
    payments_res = await client.get("/api/v1/admin/payments")
    assert payments_res.status_code == 200, payments_res.text
