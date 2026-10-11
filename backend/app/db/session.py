"""
DevPilot AI - Asynchronous Database Engine and Session Management.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from ..core.config import settings
from .base import Base

# Engine configuration depending on dialect
connect_args = {}
if "sqlite" in settings.DATABASE_URL.lower():
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    future=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency providing an async database session per request."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
