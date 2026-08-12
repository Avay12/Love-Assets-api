"""Test fixtures.

The environment is pinned *before* app.core.config is imported. Settings are
built at import time from .env, so without this the suite runs against whatever
credentials the developer happens to have configured -- which is how
`test_oauth_start_is_503_when_unconfigured` started failing on a machine with
real Google credentials in .env.
"""

import os

os.environ.update(
    {
        "DEBUG": "False",
        "SECRET_KEY": "test-secret-key-that-is-at-least-32-bytes-long",
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "PUBLIC_APP_URL": "http://localhost:8080",
        "PUBLIC_API_URL": "http://localhost:8000",
        # The test client speaks plain http, so a Secure cookie would be
        # dropped and every authenticated request would come back 401.
        "COOKIE_SECURE": "False",
        "COOKIE_SAMESITE": "lax",
        "COOKIE_DOMAIN": "",
        # Every outbound integration off: no test should reach the network.
        "GOOGLE_CLIENT_ID": "",
        "GOOGLE_CLIENT_SECRET": "",
        "GITHUB_CLIENT_ID": "",
        "GITHUB_CLIENT_SECRET": "",
        "SEVEN_API_KEY": "",
        "SMTP_USER": "",
        "SMTP_PASSWORD": "",
        "TURNSTILE_SECRET_KEY": "",
    }
)

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import AsyncClient, ASGITransport  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.core.deps import ACCESS_COOKIE, reset_rate_limits  # noqa: E402
from app.modules.auth.models import User  # noqa: E402

DEFAULT_USER = {"name": "Test User", "email": "test.user@example.com", "password": "correct-horse7"}

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    """The sliding window is process-global, so one test's requests otherwise
    count against the next one's -- /register allows only 10 per hour."""
    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def signed_in(client):
    """Register a user and leave `client` holding their session."""
    res = await client.post("/api/v1/auth/register", json=DEFAULT_USER)
    assert res.status_code == 201, res.text
    client.cookies.set(ACCESS_COOKIE, res.json()["access_token"])
    return res.json()["user"]


@pytest_asyncio.fixture
async def admin(client, db_session, signed_in):
    """Same, promoted. Role is not settable through the API by design, so the
    only way to an admin is to write the column."""
    user = await db_session.get(User, signed_in["id"])
    user.role = "admin"
    await db_session.commit()
    return signed_in
