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


FAKE_CHUNKS = [
    {
        "score": 0.88, "file_path": "app/services/commit_service.py",
        "start_line": 25, "end_line": 28, "language": "python",
        "text": "def _truncate_diff(diff):\n    ...",
    },
]


@pytest.mark.asyncio
async def test_explain_grounds_prompt_with_retrieved_context(monkeypatch):
    _set_env(monkeypatch)
    from app.rag import retriever
    from app.services import explain_service, llm_service

    async def fake_retrieve(repo_id, query, k=5):
        assert repo_id == "repo-123"
        assert query == "def foo():\n    return 42"
        return FAKE_CHUNKS

    monkeypatch.setattr(retriever, "retrieve", fake_retrieve)

    seen = {}

    async def fake_provider(system, prompt, temperature, max_tokens):
        seen["system"] = system
        seen["prompt"] = prompt
        return llm_service.LLMResult(text="This returns a constant.", input_tokens=30, output_tokens=6)

    monkeypatch.setitem(llm_service._PROVIDERS, "gemini", fake_provider)

    result, sources = await explain_service.explain(
        "repo-123", "def foo():\n    return 42", file_path="app/foo.py", language="python", cache=None,
    )

    assert result.text == "This returns a constant."
    assert sources == [
        {"file_path": "app/services/commit_service.py", "start_line": 25,
         "end_line": 28, "language": "python", "score": 0.88}
    ]
    assert "app/foo.py" in seen["prompt"]
    assert "def foo():" in seen["prompt"]
    assert "app/services/commit_service.py:25-28" in seen["prompt"]
    assert seen["system"] == explain_service.SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_explain_works_without_file_path_or_matches(monkeypatch):
    _set_env(monkeypatch)
    from app.rag import retriever
    from app.services import explain_service, llm_service

    async def fake_retrieve(repo_id, query, k=5):
        return []  # nothing relevant found in the repo

    monkeypatch.setattr(retriever, "retrieve", fake_retrieve)

    seen = {}

    async def fake_provider(system, prompt, temperature, max_tokens):
        seen["prompt"] = prompt
        return llm_service.LLMResult(text="A short explanation.", input_tokens=12, output_tokens=4)

    monkeypatch.setitem(llm_service._PROVIDERS, "gemini", fake_provider)

    result, sources = await explain_service.explain("repo-123", "x = 1 + 1", cache=None)

    assert result.text == "A short explanation."
    assert sources == []
    assert "Related context" not in seen["prompt"]  # no context block when nothing was retrieved


@pytest.mark.asyncio
async def test_explain_truncates_huge_snippets(monkeypatch):
    _set_env(monkeypatch)
    from app.rag import retriever
    from app.services import explain_service, llm_service

    async def fake_retrieve(repo_id, query, k=5):
        return []

    monkeypatch.setattr(retriever, "retrieve", fake_retrieve)

    seen = {}

    async def fake_provider(system, prompt, temperature, max_tokens):
        seen["prompt"] = prompt
        return llm_service.LLMResult(text="ok", input_tokens=1, output_tokens=1)

    monkeypatch.setitem(llm_service._PROVIDERS, "gemini", fake_provider)

    huge_code = "x" * 20_000
    await explain_service.explain("repo-123", huge_code, cache=None)

    assert "[truncated]" in seen["prompt"]
    assert len(seen["prompt"]) < 15_000
