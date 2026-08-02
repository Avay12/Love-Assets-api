import json
from typing import List, Union
from urllib.parse import urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Query params libpq understands but asyncpg does not.
_LIBPQ_ONLY = {"sslmode", "sslrootcert", "sslcert", "sslkey", "target_session_attrs", "channel_binding"}


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
    PROJECT_NAME: str = "LoveAssets API"
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Database. Accepts a plain postgresql:// URL (what a hosting provider
    # hands you) and adapts it per driver below.
    DATABASE_URL: str = "sqlite+aiosqlite:///./loveassets.db"

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

    # Integration
    SEVEN_API_KEY: str = ""

    # CORS Configuration
    CORS_ORIGINS: Union[List[str], str] = ["*"]

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
        return ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
