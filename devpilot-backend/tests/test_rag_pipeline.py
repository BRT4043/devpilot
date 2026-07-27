from pathlib import Path

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


def test_ingestion_skips_junk_and_keeps_source(tmp_path: Path, monkeypatch):
    _set_env(monkeypatch)
    from app.rag.ingestion import collect_files

    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("def hello():\n    return 'hi'\n")
    (tmp_path / "node_modules" / "lib").mkdir(parents=True)
    (tmp_path / "node_modules" / "lib" / "index.js").write_text("junk")
    (tmp_path / "logo.png").write_bytes(b"\x89PNG junk")
    (tmp_path / "empty.py").write_text("   \n")
    (tmp_path / "huge.js").write_text("x" * 600_000)

    files = collect_files(tmp_path)
    paths = [f.path for f in files]

    assert "app/main.py" in paths
    assert len(files) == 1  # everything else filtered
    assert files[0].language == "python"


def test_chunking_produces_line_numbers(monkeypatch):
    _set_env(monkeypatch)
    from app.rag.chunking import split_file
    from app.rag.ingestion import SourceFile

    code = "\n\n".join(
        f"def function_{i}():\n" + "\n".join(f"    x{j} = {j}" for j in range(30))
        for i in range(10)
    )
    f = SourceFile(path="big.py", language="python", content=code)
    chunks = split_file(f)

    assert len(chunks) > 1                      # actually split
    assert chunks[0].start_line == 1
    for c in chunks:
        assert c.file_path == "big.py"
        assert 1 <= c.start_line <= c.end_line
        assert c.text in code                   # chunks are real substrings


def test_repos_endpoints_require_auth(monkeypatch):
    _set_env(monkeypatch)
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    assert client.get("/repos").status_code == 401
    assert client.post("/repos", json={"github_full_name": "a/b"}).status_code == 401


def test_repo_name_validation(monkeypatch):
    _set_env(monkeypatch)
    from pydantic import ValidationError
    from app.schemas.repos import RepoConnectRequest
    import pytest

    RepoConnectRequest(github_full_name="anvika/chargehub")  # valid
    with pytest.raises(ValidationError):
        RepoConnectRequest(github_full_name="not a repo name!!")
