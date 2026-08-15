# Wish2Luv API

FastAPI backend for **Wish2Luv** — keepsake letters with photos, music and a
share link. Async SQLAlchemy 2.0, Alembic migrations, Postgres in production
(SQLite works for local development).

The frontend lives in [`../LoveAssets`](../LoveAssets).

---

## Quick start

```bash
python -m venv venv
venv\Scripts\Activate.ps1          # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # then fill in SECRET_KEY at minimum
alembic upgrade head
python run.py
```

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

The schema is owned by Alembic. `create_all` is deliberately not called on
startup — it only ever adds missing tables and silently ignores changes to
existing ones, so the first altered column would go unnoticed.

---

## Layout

```text
app/
├── api/
│   ├── router.py             # mounts v1 under API_V1_STR
│   └── v1/router.py          # aggregates every module router
├── core/
│   ├── config.py             # pydantic-settings, reads .env
│   ├── crypto.py             # argon2, JWT, purpose tokens, Fernet at rest
│   ├── database.py           # async engine + get_db session dependency
│   └── deps.py               # current_user, cookies, rate limiter, require_admin
├── db/base.py                # imports every model so Alembic can see it
├── modules/                  # one package per domain
│   ├── auth/                 # register, login, sessions, OAuth
│   ├── letters/              # the five letter types + generic CRUD
│   ├── templates/            # reveal-template catalogue
│   ├── music/                # featured tracks + search
│   ├── media/                # photo upload
│   ├── delivery/             # email, SMS, voice, Turnstile
│   ├── payments/             # order records
│   ├── admin/                # admin dashboard
│   └── health/
├── utils/storage.py          # upload validation and streaming write
└── main.py
migrations/                   # Alembic
scripts/make_admin.py         # the only way to promote an account
tests/
```

Each module holds its own `router.py`, `schemas.py`, and where it needs one a
`models.py` and `service.py`.

---

## Endpoints

Everything is under `/api/v1`. **Auth** column: *public* needs nothing,
*session* needs a signed-in user, *owner* needs the letter's owner (an admin
also passes), *admin* needs `role = "admin"`.

| Method | Path | Auth | |
|---|---|---|---|
| `GET` | `/health` | public | Pings the database |
| `POST` | `/auth/register` | public | Creates an account. `role` is **not** accepted |
| `POST` | `/auth/login` | public | |
| `POST` | `/auth/logout` | public | Revokes the refresh token server-side |
| `POST` | `/auth/refresh` | public | Rotates the session |
| `GET` | `/auth/me` | session | |
| `POST` | `/auth/forgot-password` | public | Emails a 30-minute reset link |
| `POST` | `/auth/reset-password` | public | Consumes the link, revokes all sessions |
| `POST` | `/auth/verify-email` | public | |
| `GET` | `/auth/providers` | public | Which OAuth providers are configured |
| `GET` | `/auth/oauth/{provider}` | public | `google` or `github` |
| `GET` | `/auth/oauth/{provider}/callback` | public | Redirect target |
| `POST` | `/{type}/` | public | Create — attached to the session if there is one |
| `GET` | `/{type}/` | admin | List by type |
| `GET` | `/{type}/{slug}` | public | Open a shared letter |
| `DELETE` | `/{type}/{slug}` | owner | |
| `GET` | `/letters/my-letters` | session | The caller's letters |
| `POST` `GET` | `/letters/` | public / admin | Generic create, admin-only list |
| `GET` `PUT` `DELETE` | `/letters/{slug}` | public / owner / owner | |
| `POST` | `/delivery/schedule` | owner | Re-target a letter's delivery |
| `GET` | `/payments/my-payments` | session | |
| `GET` | `/templates/`, `/templates/{id}` | public | |
| `GET` | `/music/featured`, `/music/search` | public | |
| `POST` | `/media/upload` | public | Photo or audio, 10 MB cap |
| `GET` | `/admin/stats`, `/admin/users`, `/admin/letters`, `/admin/payments` | admin | |
| `POST` | `/admin/users/invite` | admin | Emails a set-your-password link |
| `DELETE` | `/admin/letters/{slug}` | admin | |
| `POST` | `/admin/change-password` | session | |

`{type}` is one of `love-letters`, `valentine-letters`, `birthday-letters`,
`birthday-invitations`, `wedding-invitations`.

### Why listing is admin-only

A letter's slug is its capability: 10 random characters from `secrets`, handed
to the recipient. Reading one by slug is therefore public — that is the whole
product. Listing is not, because a public list hands out every letter's names,
private message and `delivery_contact` (recipient phone numbers and email
addresses), which would make the slug entropy pointless.

---

## Notes on operation

**Admins.** `role` is never settable through the API. Promote an account with:

```bash
python scripts/make_admin.py alex@example.com
```

**One worker only, for now.** The rate limiter (`app/core/deps.py`) and the
OAuth state map (`app/modules/auth/router.py`) are in-process dictionaries.
With more than one worker the rate limit multiplies by worker count and an
OAuth callback can land on a process that never saw the handshake start. Both
need to move to Redis (`REDIS_URL` is reserved in `.env.example`) before
scaling out.

**Payments are not implemented.** Creating a letter records an order at
`LETTER_PRICE` with status `Pending`. No gateway is wired up, so nothing ever
moves it to `Paid` and the admin revenue figures read zero. That is accurate,
not broken.

**Unconfigured integrations degrade quietly.** With no `SEVEN_API_KEY`,
`SMTP_USER`/`SMTP_PASSWORD` or `TURNSTILE_SECRET_KEY`, SMS/voice, email and the
captcha check are skipped rather than failing the request — so a fresh checkout
runs with an empty `.env`. Password reset and invite links are written to the
log when email is unavailable.

---

## Tests

```bash
pytest
```

`tests/conftest.py` pins the whole environment before settings are built, so the
suite ignores your `.env`, uses an in-memory SQLite database and never reaches
the network. CI runs it, plus `alembic upgrade head` against an empty database,
before the deploy job is allowed to start.
