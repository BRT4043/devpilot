from fastapi.testclient import TestClient


def test_health(monkeypatch):
    for k, v in {
        "JWT_SECRET": "test", "TOKEN_ENCRYPTION_KEY": "test",
        "GITHUB_CLIENT_ID": "x", "GITHUB_CLIENT_SECRET": "x",
        "GITHUB_CALLBACK_URL": "http://localhost/cb",
        "DATABASE_URL": "postgresql+asyncpg://u:p@localhost/db",
        "REDIS_URL": "redis://localhost:6379/0",
        "QDRANT_URL": "http://localhost:6333",
    }.items():
        monkeypatch.setenv(k, v)
    from app.main import app
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
