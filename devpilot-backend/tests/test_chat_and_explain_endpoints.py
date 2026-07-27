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
    }.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()


def test_chat_endpoints_require_auth(monkeypatch):
    _set_env(monkeypatch)
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    fake_repo_id = "11111111-1111-1111-1111-111111111111"
    fake_session_id = "22222222-2222-2222-2222-222222222222"

    assert client.post(f"/repos/{fake_repo_id}/chat", json={"message": "hi"}).status_code == 401
    assert client.get(f"/repos/{fake_repo_id}/sessions").status_code == 401
    assert client.get(f"/sessions/{fake_session_id}/messages").status_code == 401


def test_explain_endpoint_requires_auth(monkeypatch):
    _set_env(monkeypatch)
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    fake_repo_id = "11111111-1111-1111-1111-111111111111"
    r = client.post(f"/repos/{fake_repo_id}/explain", json={"code": "x = 1"})
    assert r.status_code == 401


def test_chat_request_validation(monkeypatch):
    _set_env(monkeypatch)
    import pytest
    from pydantic import ValidationError
    from app.schemas.chat import ChatRequest

    ChatRequest(message="How does auth work?")  # valid, no session
    with pytest.raises(ValidationError):
        ChatRequest(message="")  # empty message rejected


def test_explain_request_validation(monkeypatch):
    _set_env(monkeypatch)
    import pytest
    from pydantic import ValidationError
    from app.schemas.explain import ExplainRequest

    ExplainRequest(code="def foo(): pass")  # valid, no file_path needed
    with pytest.raises(ValidationError):
        ExplainRequest(code="")  # empty snippet rejected
