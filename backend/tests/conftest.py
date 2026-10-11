"""
DevPilot AI - PyTest Configuration and Fixtures for Backend Tests.
"""

import sys
import os
import json
from typing import AsyncGenerator, Generator
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from fastapi.testclient import TestClient

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORKSPACE_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.main import app
from app.models import Base
from app.db.session import get_db

# Isolated test engine using in-memory SQLite
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
test_session_factory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture
def sample_spec_content() -> str:
    """Load the official sample e-commerce OpenAPI JSON specification."""
    spec_path = os.path.join(WORKSPACE_ROOT, "sample-api", "openapi", "sample_ecommerce_spec.json")
    with open(spec_path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
async def async_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated, freshly-initialized database session per test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def client(sample_spec_content: str) -> Generator[TestClient, None, None]:
    """TestClient with overridden database dependency using test engine."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    # Create tables before starting client
    import asyncio

    async def _init() -> None:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()
