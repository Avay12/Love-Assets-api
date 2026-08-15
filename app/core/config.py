import json
from typing import List, Union
from urllib.parse import urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Query params libpq understands but asyncpg does not.
_LIBPQ_ONLY = {"sslmode", "sslrootcert", "sslcert", "sslkey", "target_session_attrs", "channel_binding"}

_DEFAULT_CORS_ORIGINS = [
    "http://localhost:8080",
    "http://localhost:5173",
    "http://localhost:3000",
    "https://wish2luv.com",
    "https://www.wish2luv.com",
]


def _strip_libpq_params(url: str) -> str:
    parts = urlsplit(url)
    if not parts.query:
        return url
    kept = [
        (k, v)
        for pair in parts.query.split("&")
        if pair
        for k, _, v in [pair.partition("=")]
        if k not in _LIBPQ_ONLY
    ]
    return urlunsplit(parts._replace(query=urlencode(kept)))


class Settings(BaseSettings):
    PROJECT_NAME: str = "Wish2Luv API"
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Database. Accepts a plain postgresql:// URL (what a hosting provider
    # hands you) and adapts it per driver below.
    DATABASE_URL: str = "sqlite+aiosqlite:///./wish2love.db"

    @property
    def async_database_url(self) -> str:
        """URL for the app's async engine.

        asyncpg rejects libpq-style query params such as ``sslmode``; SSL is
        configured through connect_args instead, so they are stripped here.
        """
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):  # some providers still emit this
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return _strip_libpq_params(url) if "asyncpg" in url else url

    @property
    def sync_database_url(self) -> str:
        """URL for Alembic, which runs migrations synchronously."""
        url = self.DATABASE_URL
        for prefix, repl in (
            ("postgresql+asyncpg://", "postgresql+psycopg2://"),
            ("postgresql://", "postgresql+psycopg2://"),
            ("postgres://", "postgresql+psycopg2://"),
            ("sqlite+aiosqlite://", "sqlite://"),
        ):
            if url.startswith(prefix):
                return url.replace(prefix, repl, 1)
        return url

    @property
    def is_postgres(self) -> bool:
        return "postgres" in self.DATABASE_URL

    # Storage
    UPLOAD_DIR: str = "./uploads"

    # Public base URL of the frontend, used to build the share link that goes
    # out in SMS/voice messages. Previously hardcoded to a placeholder domain.
    PUBLIC_APP_URL: str = "http://localhost:8080"

    # Public base URL of this API, used to turn stored upload paths into
    # absolute URLs the browser can load cross-origin.
    PUBLIC_API_URL: str = "http://localhost:8000"

    # ---- auth -------------------------------------------------------
    # Signs access tokens and encrypts stored OAuth tokens. Override in .env;
    # the default exists only so a fresh checkout boots. Must be >= 32 bytes,
    # the minimum RFC 7518 gives for an HMAC-SHA256 key.
    SECRET_KEY: str = ""

    @field_validator("SECRET_KEY")
    @classmethod
    def _secret_long_enough(cls, v: str) -> str:
        if v and len(v.encode()) < 32:
            raise ValueError("SECRET_KEY must be at least 32 bytes (RFC 7518 for HMAC-SHA256)")
        return v
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 30

    # Cookie flags. SECURE must be on in production (HTTPS only).
    COOKIE_SECURE: bool = False
    COOKIE_DOMAIN: str = ""
    COOKIE_SAMESITE: str = "lax"

    # Google OAuth. Create credentials at console.cloud.google.com and add
    # <PUBLIC_API_URL>/api/v1/auth/oauth/google/callback as a redirect URI.
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    @property
    def google_enabled(self) -> bool:
        return bool(self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET)

    @property
    def github_enabled(self) -> bool:
        return bool(self.GITHUB_CLIENT_ID and self.GITHUB_CLIENT_SECRET)

    # Integration
    SEVEN_API_KEY: str = ""

    # SMTP / Brevo Email Integration
    SMTP_HOST: str = "smtp-relay.brevo.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    MAIL_FROM: str = "Wish2Luv <no-reply@wish2luv.com>"

    @property
    def smtp_enabled(self) -> bool:
        return bool(self.SMTP_USER and self.SMTP_PASSWORD)

    # What a letter costs. No payment gateway is wired up yet, so orders are
    # recorded as "Pending" at this price and only move to "Paid" once one is.
    LETTER_PRICE: float = 4.99
    LETTER_CURRENCY: str = "USD"

    # Captcha / Bot Protection
    TURNSTILE_SECRET_KEY: str = ""

    @property
    def turnstile_enabled(self) -> bool:
        return bool(self.TURNSTILE_SECRET_KEY)

    # CORS Configuration. A wildcard is rejected -- see the validator below.
    CORS_ORIGINS: Union[List[str], str] = _DEFAULT_CORS_ORIGINS.copy()

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return _DEFAULT_CORS_ORIGINS.copy()

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def _no_wildcard_origin(cls, v: List[str]) -> List[str]:
        """The API authenticates with cookies, and `allow_credentials=True`
        alongside a wildcard origin lets any site on the internet make
        authenticated calls with a visitor's session. List the origins."""
        if "*" in v:
            raise ValueError(
                "CORS_ORIGINS must not contain '*': this API sends credentials, "
                "so every allowed origin has to be named explicitly."
            )
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
