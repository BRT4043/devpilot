import uuid

import pytest
from cryptography.fernet import Fernet


def _set_env(monkeypatch):
    for k, v in {
        "JWT_SECRET": "test-secret",
        "TOKEN_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "GITHUB_CLIENT_ID": "x", "GITHUB_CLIENT_SECRET": "x",
        "GITHUB_CALLBACK_URL": "http://localhost/cb",
        "DATABASE_URL": "postgresql+asyncpg://u:p@localhost/db",
        "REDIS_URL": "redis://localhost:6379/0",
        "QDRANT_URL": "http://localhost:6333",
        "LLM_PROVIDER": "gemini",
    }.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()


class FakeRedis:
    """Dict-backed stand-in for redis.asyncio.Redis."""

    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value

    async def aclose(self):
        pass


@pytest.mark.asyncio
async def test_complete_uses_cache_on_second_call(monkeypatch):
    _set_env(monkeypatch)
    from app.services import llm_service

    calls = {"n": 0}

    async def fake_provider(system, prompt, temperature, max_tokens):
        calls["n"] += 1
        return llm_service.LLMResult(text="feat: add auth", input_tokens=100, output_tokens=10)

    monkeypatch.setitem(llm_service._PROVIDERS, "gemini", fake_provider)

    cache = FakeRedis()
    r1 = await llm_service.complete("some prompt", cache=cache)
    r2 = await llm_service.complete("some prompt", cache=cache)

    assert calls["n"] == 1          # provider hit exactly once
    assert r1.cached is False
    assert r2.cached is True
    assert r2.text == "feat: add auth"


@pytest.mark.asyncio
async def test_commit_service_strips_fences_and_truncates(monkeypatch):
    _set_env(monkeypatch)
    from app.services import commit_service, llm_service

    seen = {}

    async def fake_provider(system, prompt, temperature, max_tokens):
        seen["prompt"] = prompt
        return llm_service.LLMResult(
            text="```\nfix(api): handle empty diff\n```",
            input_tokens=50, output_tokens=8,
        )

    monkeypatch.setitem(llm_service._PROVIDERS, "gemini", fake_provider)

    huge_diff = "x" * 50_000
    result = await commit_service.generate(huge_diff, "conventional", cache=None)

    assert result.text == "fix(api): handle empty diff"
    assert "[diff truncated]" in seen["prompt"]
    assert len(seen["prompt"]) < 20_000


def test_commit_endpoint_requires_auth(monkeypatch):
    _set_env(monkeypatch)
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    r = client.post("/commit-message", json={"diff": "+ hello"})
    assert r.status_code == 401
