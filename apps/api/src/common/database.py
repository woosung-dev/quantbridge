"""SQLAlchemy AsyncEngine 및 AsyncSession 팩토리.

`get_async_session()` 이 요청 1건당 세션을 yield 하는 FastAPI 의존성이며, commit 은
호출한 Service 의 책임이다 (실패 시 자동 rollback).
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import secret_value, settings

engine = create_async_engine(
    secret_value(settings.database_url),
    echo=settings.debug,
    pool_pre_ping=True,
    future=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession. Lifetime is one request. Commit is the Service's responsibility."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
