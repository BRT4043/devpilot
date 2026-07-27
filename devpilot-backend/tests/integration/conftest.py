"""Fixtures for tests that need a real Postgres (not fakeable — real SQL,
real transactions, real constraints). Skips the whole package if no test
database is configured, so `pytest -q` in the plain unit-test job stays
fast and DB-free; set TEST_DATABASE_URL to opt in.

    docker compose -f docker-compose.test.yml up -d
    export TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/devpilot_test
    pytest -m integration
"""

import os

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    collect_ignore_glob = ["*"]


def _set_env(monkeypatch):
    for k, v in {
        "JWT_SECRET": "test-secret",
        "TOKEN_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "GITHUB_CLIENT_ID": "x", "GITHUB_CLIENT_SECRET": "x",
        "GITHUB_CALLBACK_URL": "http://localhost/cb",
        "DATABASE_URL": TEST_DATABASE_URL or "postgresql+asyncpg://u:p@localhost/db",
        "REDIS_URL": "redis://localhost:6379/0",
        "QDRANT_URL": "http://localhost:6333",
        "LLM_PROVIDER": "gemini",
    }.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()


class FakeRedis:
    """Dict-backed stand-in for redis.asyncio.Redis (same shape as the one
    used in tests/test_llm_and_commits.py) — no real Redis needed either."""

    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value

    async def aclose(self):
        pass


@pytest.fixture
async def db_engine(monkeypatch):
    """A real async engine pointed at TEST_DATABASE_URL, with all tables
    created fresh and dropped again after the test. Built directly (not via
    app.db.engine) since app.db binds its module-level engine at import
    time — before we've had a chance to set DATABASE_URL for this test."""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set")

    _set_env(monkeypatch)
    from app.db import Base
    import app.models.models  # noqa: F401  registers tables on Base.metadata

    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.fixture
async def db(db_engine):
    """A real AsyncSession against the freshly-created schema."""
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
