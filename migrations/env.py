"""Alembic environment.

The database URL is read from the app's settings (and therefore from .env),
never from alembic.ini -- the connection string is a secret and must not sit
in a tracked file.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.core.config import settings

# Importing the model package registers every table on Base.metadata, which is
# what --autogenerate diffs against.
from app.db.base import Base  # noqa: F401

config = context.config
# Deliberately not config.set_main_option(): alembic.ini goes through
# ConfigParser, which treats a '%' in the URL (e.g. %40 for '@' in a
# password) as interpolation syntax and raises. The URL is handed straight
# to the engine below instead.

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _connect_args() -> dict:
    if settings.is_postgres and "sslmode=disable" in settings.DATABASE_URL:
        return {"ssl": False}
    return {}


def run_migrations_offline() -> None:
    context.configure(
        url=settings.async_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        # SQLite cannot ALTER most things; batch mode rebuilds the table.
        render_as_batch=not settings.is_postgres,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        {**config.get_section(config.config_ini_section, {}), "sqlalchemy.url": settings.async_database_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=_connect_args(),
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
