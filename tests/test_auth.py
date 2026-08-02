import pytest

from app.api.deps import ACCESS_COOKIE, REFRESH_COOKIE, reset_rate_limits

CREDS = {"name": "Alex Hart", "email": "alex@example.com", "password": "correct-horse7"}


@pytest.fixture(autouse=True)
def _clear_limits():
    # The sliding window is process-global; without this the 10-per-window
    # login limit trips partway through the suite.
    reset_rate_limits()
    yield
    reset_rate_limits()


async def register(client, **over):
    return await client.post("/api/v1/auth/register", json={**CREDS, **over})


# ------------------------------------------------------------- register


@pytest.mark.asyncio
async def test_register_returns_user_and_sets_cookies(client):
    res = await register(client)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["user"]["email"] == "alex@example.com"
    assert body["user"]["has_password"] is True
    assert body["access_token"]
    assert ACCESS_COOKIE in res.cookies and REFRESH_COOKIE in res.cookies


@pytest.mark.asyncio
async def test_password_hash_is_never_returned(client):
    res = await register(client)
    assert "password" not in res.text.lower().replace("has_password", "")


@pytest.mark.asyncio
async def test_duplicate_email_rejected(client):
    await register(client)
    assert (await register(client)).status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["short1", "nodigitshere", "12345678"])
async def test_weak_passwords_rejected(client, bad):
    assert (await register(client, password=bad)).status_code == 422


# ---------------------------------------------------------------- login


@pytest.mark.asyncio
async def test_login_succeeds(client):
    await register(client)
    res = await client.post("/api/v1/auth/login", json={"email": CREDS["email"], "password": CREDS["password"]})
    assert res.status_code == 200
    assert res.json()["user"]["email"] == CREDS["email"]


@pytest.mark.asyncio
async def test_login_errors_are_identical_for_unknown_and_wrong_password(client):
    await register(client)
    wrong = await client.post("/api/v1/auth/login", json={"email": CREDS["email"], "password": "wrongpass1"})
    unknown = await client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrongpass1"})
    assert wrong.status_code == unknown.status_code == 401
    # Identical wording: anything else reveals which emails are registered.
    assert wrong.json()["detail"] == unknown.json()["detail"]


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    assert (await client.get("/api/v1/auth/me")).status_code == 401


@pytest.mark.asyncio
async def test_me_returns_the_signed_in_user(client):
    await register(client)
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 200
    assert res.json()["email"] == CREDS["email"]


@pytest.mark.asyncio
async def test_bearer_token_also_authenticates(client):
    token = (await register(client)).json()["access_token"]
    client.cookies.clear()
    res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200


# ------------------------------------------------------------- sessions


@pytest.mark.asyncio
async def test_refresh_rotates_the_token(client):
    await register(client)
    first = client.cookies.get(REFRESH_COOKIE)
    res = await client.post("/api/v1/auth/refresh")
    assert res.status_code == 200
    assert client.cookies.get(REFRESH_COOKIE) != first, "refresh token must rotate"


@pytest.mark.asyncio
async def test_refresh_token_reuse_revokes_the_family(client):
    """Replaying a rotated token is the stolen-token signal: the whole family
    dies, not just the replayed row."""
    await register(client)
    stolen = client.cookies.get(REFRESH_COOKIE)

    assert (await client.post("/api/v1/auth/refresh")).status_code == 200  # rotates
    good = client.cookies.get(REFRESH_COOKIE)

    client.cookies.set(REFRESH_COOKIE, stolen)
    replay = await client.post("/api/v1/auth/refresh")
    assert replay.status_code == 401

    # the legitimate token is now dead too
    client.cookies.set(REFRESH_COOKIE, good)
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_server_side(client):
    await register(client)
    refresh = client.cookies.get(REFRESH_COOKIE)
    assert (await client.post("/api/v1/auth/logout")).status_code == 204

    client.cookies.set(REFRESH_COOKIE, refresh)
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401


# --------------------------------------------------------- reset / verify


@pytest.mark.asyncio
async def test_forgot_password_reply_is_identical_for_unknown_email(client):
    await register(client)
    known = await client.post("/api/v1/auth/forgot-password", json={"email": CREDS["email"]})
    unknown = await client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()


@pytest.mark.asyncio
async def test_reset_password_invalidates_sessions(client):
    from app.core.crypto import sign_purpose_token

    uid = (await register(client)).json()["user"]["id"]
    refresh = client.cookies.get(REFRESH_COOKIE)
    token = sign_purpose_token("reset-password", str(uid), minutes=30)

    res = await client.post("/api/v1/auth/reset-password", json={"token": token, "password": "brand-new-pw9"})
    assert res.status_code == 204

    client.cookies.set(REFRESH_COOKIE, refresh)
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401

    ok = await client.post("/api/v1/auth/login", json={"email": CREDS["email"], "password": "brand-new-pw9"})
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_reset_with_a_forged_token_is_rejected(client):
    await register(client)
    assert (
        await client.post("/api/v1/auth/reset-password", json={"token": "not-a-token", "password": "brand-new-pw9"})
    ).status_code == 400


@pytest.mark.asyncio
async def test_verify_email(client):
    from app.core.crypto import sign_purpose_token

    uid = (await register(client)).json()["user"]["id"]
    assert (await client.get("/api/v1/auth/me")).json()["email_verified"] is False

    token = sign_purpose_token("verify-email", str(uid), minutes=60)
    assert (await client.post("/api/v1/auth/verify-email", json={"token": token})).status_code == 204
    assert (await client.get("/api/v1/auth/me")).json()["email_verified"] is True


@pytest.mark.asyncio
async def test_purpose_tokens_are_not_interchangeable(client):
    """A verification token must not double as a password reset."""
    from app.core.crypto import sign_purpose_token

    uid = (await register(client)).json()["user"]["id"]
    verify_token = sign_purpose_token("verify-email", str(uid), minutes=60)
    res = await client.post("/api/v1/auth/reset-password", json={"token": verify_token, "password": "brand-new-pw9"})
    assert res.status_code == 400


# ------------------------------------------------------------------ oauth


@pytest.mark.asyncio
async def test_oauth_start_is_503_when_unconfigured(client):
    assert (await client.get("/api/v1/auth/oauth/google")).status_code == 503


@pytest.mark.asyncio
async def test_unknown_provider_404s(client):
    assert (await client.get("/api/v1/auth/oauth/myspace")).status_code == 404


@pytest.mark.asyncio
async def test_oauth_start_redirects_with_pkce_and_state(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "cid", raising=False)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "secret", raising=False)

    res = await client.get("/api/v1/auth/oauth/google", follow_redirects=False)
    assert res.status_code == 302
    loc = res.headers["location"]
    assert loc.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "code_challenge=" in loc and "code_challenge_method=S256" in loc
    assert "response_type=code" in loc and "state=" in loc
    assert "response_type=token" not in loc  # never the implicit flow


@pytest.mark.asyncio
async def test_oauth_callback_rejects_unknown_state(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "cid", raising=False)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "secret", raising=False)

    res = await client.get(
        "/api/v1/auth/oauth/google/callback?code=abc&state=forged", follow_redirects=False
    )
    assert res.status_code == 302
    assert "error=bad_state" in res.headers["location"]


@pytest.mark.asyncio
async def test_oauth_links_to_an_existing_password_account(client):
    """Signing in with Google using a registered email must attach to that
    account, not silently create a duplicate."""
    from app.core.database import get_db
    from app.main import app
    from app.services.auth_service import AuthService

    uid = (await register(client)).json()["user"]["id"]

    db = await anext(app.dependency_overrides[get_db]())
    user = await AuthService.link_or_create(
        db, provider="google", provider_account_id="g-123", email=CREDS["email"], name="Alex Hart"
    )
    assert user.id == uid, "should link, not create a second account"
    assert "google" in [i.provider for i in user.identities]

    # and the same provider account resolves back to the same user
    again = await AuthService.link_or_create(
        db, provider="google", provider_account_id="g-123", email=CREDS["email"], name="Alex Hart"
    )
    assert again.id == uid


@pytest.mark.asyncio
async def test_oauth_only_account_has_no_password(client):
    from app.core.database import get_db
    from app.main import app
    from app.services.auth_service import AuthService

    db = await anext(app.dependency_overrides[get_db]())
    user = await AuthService.link_or_create(
        db, provider="google", provider_account_id="g-999", email="new@example.com", name="New Person"
    )
    assert user.password_hash is None
    assert user.email_verified_at is not None  # the provider vouched for it

    # a password login attempt must still fail cleanly, not error
    res = await client.post("/api/v1/auth/login", json={"email": "new@example.com", "password": "whatever12"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_stored_oauth_tokens_are_encrypted(client):
    from app.core.crypto import decrypt
    from app.core.database import get_db
    from app.main import app
    from app.services.auth_service import AuthService

    db = await anext(app.dependency_overrides[get_db]())
    user = await AuthService.link_or_create(
        db,
        provider="google",
        provider_account_id="g-enc",
        email="enc@example.com",
        name="Enc",
        access_token="ya29.super-secret",
    )
    stored = user.identities[0].access_token
    assert stored != "ya29.super-secret", "provider token must not be stored in clear text"
    assert decrypt(stored) == "ya29.super-secret"


# ------------------------------------------------------------ rate limit


@pytest.mark.asyncio
async def test_login_is_rate_limited(client):
    await register(client)
    codes = []
    for _ in range(13):
        r = await client.post("/api/v1/auth/login", json={"email": CREDS["email"], "password": "wrongpass1"})
        codes.append(r.status_code)
    assert 429 in codes, "brute force must eventually be throttled"


# ------------------------------------------------------------------- role


@pytest.mark.asyncio
async def test_new_accounts_are_not_admin(client):
    res = await register(client)
    assert res.json()["user"]["role"] == "user"
    assert res.json()["user"]["is_admin"] is False


@pytest.mark.asyncio
async def test_role_cannot_be_set_through_registration(client):
    """A self-service role field would be straight privilege escalation."""
    res = await client.post("/api/v1/auth/register", json={**CREDS, "role": "admin", "is_admin": True})
    assert res.status_code == 201
    assert res.json()["user"]["role"] == "user"


@pytest.mark.asyncio
async def test_admin_flag_follows_the_stored_role(client):
    from app.core.database import get_db
    from app.main import app
    from app.services.auth_service import AuthService

    await register(client)
    db = await anext(app.dependency_overrides[get_db]())
    user = await AuthService.get_by_email(db, CREDS["email"])
    user.role = "admin"
    await db.commit()

    me = (await client.get("/api/v1/auth/me")).json()
    assert me["role"] == "admin" and me["is_admin"] is True


@pytest.mark.asyncio
async def test_require_admin_returns_404_for_non_admins(client):
    """404 not 403 -- a 403 confirms the route exists."""
    from fastapi import HTTPException

    from app.api.deps import require_admin
    from app.core.database import get_db
    from app.main import app
    from app.services.auth_service import AuthService

    await register(client)
    db = await anext(app.dependency_overrides[get_db]())
    user = await AuthService.get_by_email(db, CREDS["email"])

    with pytest.raises(HTTPException) as err:
        await require_admin(user)
    assert err.value.status_code == 404

    user.role = "admin"
    assert (await require_admin(user)) is user
