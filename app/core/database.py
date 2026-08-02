from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

def _connect_args() -> dict:
    if settings.DATABASE_URL.startswith("sqlite"):
        return {"check_same_thread": False}
    if settings.is_postgres:
        # asyncpg takes ssl as a connect arg, not a URL param. The URL's
        # sslmode is stripped in config; honour "disable" here.
        return {"ssl": False} if "sslmode=disable" in settings.DATABASE_URL else {}
    return {}


engine = create_async_engine(
    settings.async_database_url,
    echo=settings.DEBUG,
    connect_args=_connect_args(),
    # A pooled remote database drops idle connections; recycle before it does
    # and check liveness on checkout so the first request after a lull works.
    pool_pre_ping=settings.is_postgres,
    pool_recycle=1800 if settings.is_postgres else -1,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
