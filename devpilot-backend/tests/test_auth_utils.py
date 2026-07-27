import uuid

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


def test_jwt_round_trip(monkeypatch):
    _set_env(monkeypatch)
    from app.services import auth_service
    uid = uuid.uuid4()
    token = auth_service.create_jwt(uid)
    assert auth_service.decode_jwt(token) == uid


def test_jwt_rejects_garbage(monkeypatch):
    _set_env(monkeypatch)
    from app.services import auth_service
    assert auth_service.decode_jwt("not-a-token") is None


def test_token_encryption_round_trip(monkeypatch):
    _set_env(monkeypatch)
    from app.services import auth_service
    secret = "gho_example_github_token"
    enc = auth_service.encrypt_token(secret)
    assert enc != secret
    assert auth_service.decrypt_token(enc) == secret
