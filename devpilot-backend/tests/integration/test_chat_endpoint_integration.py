import uuid

import httpx
import pytest

from tests.integration.conftest import FakeRedis


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_endpoint_full_stack(db_engine, monkeypatch):
    """Exercises the real router -> service -> DB path end to end. Only the
    external calls (LLM provider, vector search, Redis cache) are faked —
    everything else, including the FastAPI dependency wiring and the actual
    SQL, is real."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.db import get_db
    from app.deps import get_current_user
    from app.main import app
    from app.models.models import Repo, User
    from app.rag import retriever
    from app.services import llm_service

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    user = User(id=uuid.uuid4(), github_id=99, username="anvika", github_token_enc="enc")
    repo = Repo(id=uuid.uuid4(), user_id=user.id, github_full_name="anvika/devpilot", index_status="ready")

    async with session_factory() as seed_db:
        seed_db.add_all([user, repo])
        await seed_db.commit()

    async def override_get_db():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user
    monkeypatch.setattr("app.routers.chat.get_redis", lambda: FakeRedis())

    async def fake_retrieve(repo_id, query, k=8):
        assert repo_id == str(repo.id)
        return [{
            "score": 0.95, "file_path": "app/services/chat_service.py",
            "start_line": 1, "end_line": 10, "language": "python", "text": "...",
        }]

    monkeypatch.setattr(retriever, "retrieve", fake_retrieve)

    async def fake_provider(system, prompt, temperature, max_tokens):
        return llm_service.LLMResult(text="Full-stack answer.", input_tokens=5, output_tokens=5)

    monkeypatch.setitem(llm_service._PROVIDERS, "gemini", fake_provider)

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(f"/repos/{repo.id}/chat", json={"message": "Hi there"})
            assert r.status_code == 200
            body = r.json()
            assert body["message"]["content"] == "Full-stack answer."
            assert body["sources"][0]["file_path"] == "app/services/chat_service.py"
            session_id = body["session"]["id"]

            r2 = await client.get(f"/repos/{repo.id}/sessions")
            assert r2.status_code == 200
            assert len(r2.json()) == 1
            assert r2.json()[0]["id"] == session_id

            r3 = await client.get(f"/sessions/{session_id}/messages")
            assert r3.status_code == 200
            assert [m["role"] for m in r3.json()] == ["user", "assistant"]

            # a session/repo owned by someone else must 404, not leak data
            other_user = User(id=uuid.uuid4(), github_id=100, username="intruder", github_token_enc="enc")
            app.dependency_overrides[get_current_user] = lambda: other_user
            r4 = await client.get(f"/repos/{repo.id}/sessions")
            assert r4.status_code == 404
            r5 = await client.get(f"/sessions/{session_id}/messages")
            assert r5.status_code == 404
    finally:
        app.dependency_overrides.clear()
