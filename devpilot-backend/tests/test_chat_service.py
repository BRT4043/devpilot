import uuid
from datetime import UTC, datetime

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


class FakeDB:
    """Minimal async stand-in for AsyncSession — just enough of the ORM
    session surface (get/add/commit/refresh) for chat_service's unit tests.
    Real query execution (list_sessions / get_session_messages) needs a real
    database and is exercised in integration/manual testing instead.
    """

    def __init__(self, existing: dict | None = None):
        self._existing = existing or {}   # id -> object, for db.get()
        self.added = []
        self.commits = 0

    async def get(self, model, id_):
        return self._existing.get(id_)

    def add(self, obj):
        self.added.append(obj)
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(UTC)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        pass


FAKE_CHUNKS = [
    {
        "score": 0.91, "file_path": "app/services/auth_service.py",
        "start_line": 39, "end_line": 42, "language": "python",
        "text": "def create_jwt(user_id):\n    ...",
    },
    {
        "score": 0.77, "file_path": "app/deps.py",
        "start_line": 14, "end_line": 26, "language": "python",
        "text": "async def get_current_user(...):\n    ...",
    },
]


def _make_repo(index_status="ready"):
    from app.models.models import Repo
    return Repo(
        id=uuid.uuid4(), user_id=uuid.uuid4(),
        github_full_name="anvika/devpilot", index_status=index_status,
    )


def _make_user(id_=None):
    from app.models.models import User
    return User(id=id_ or uuid.uuid4(), github_id=1, username="anvika", github_token_enc="x")


@pytest.mark.asyncio
async def test_get_or_create_session_creates_when_no_id(monkeypatch):
    _set_env(monkeypatch)
    from app.services import chat_service

    repo = _make_repo()
    user = _make_user()
    db = FakeDB()

    session = await chat_service.get_or_create_session(db, repo, user, None)

    assert session.repo_id == repo.id
    assert session.user_id == user.id
    assert session in db.added
    assert db.commits == 1


@pytest.mark.asyncio
async def test_get_or_create_session_rejects_wrong_owner(monkeypatch):
    _set_env(monkeypatch)
    from app.models.models import ChatSession
    from app.services import chat_service

    repo = _make_repo()
    user = _make_user()
    other_users_session = ChatSession(id=uuid.uuid4(), repo_id=repo.id, user_id=uuid.uuid4())
    db = FakeDB(existing={other_users_session.id: other_users_session})

    with pytest.raises(chat_service.ChatError):
        await chat_service.get_or_create_session(db, repo, user, other_users_session.id)


@pytest.mark.asyncio
async def test_get_or_create_session_rejects_unknown_id(monkeypatch):
    _set_env(monkeypatch)
    from app.services import chat_service

    repo = _make_repo()
    user = _make_user()
    db = FakeDB()

    with pytest.raises(chat_service.ChatError):
        await chat_service.get_or_create_session(db, repo, user, uuid.uuid4())


@pytest.mark.asyncio
async def test_send_message_rejects_repo_not_ready(monkeypatch):
    _set_env(monkeypatch)
    from app.models.models import ChatSession
    from app.services import chat_service

    repo = _make_repo(index_status="indexing")
    session = ChatSession(id=uuid.uuid4(), repo_id=repo.id, user_id=uuid.uuid4())
    db = FakeDB()

    with pytest.raises(chat_service.ChatError):
        await chat_service.send_message(db, repo, session, "How does auth work?")

    assert db.added == []  # nothing persisted once we bail out early


@pytest.mark.asyncio
async def test_send_message_grounds_prompt_and_saves_both_messages(monkeypatch):
    _set_env(monkeypatch)
    from app.models.models import ChatSession
    from app.rag import retriever
    from app.services import chat_service, llm_service

    repo = _make_repo(index_status="ready")
    session = ChatSession(id=uuid.uuid4(), repo_id=repo.id, user_id=uuid.uuid4(), title=None)
    db = FakeDB()

    async def fake_retrieve(repo_id, query, k=8):
        assert repo_id == str(repo.id)
        assert query == "How does auth work?"
        return FAKE_CHUNKS

    monkeypatch.setattr(retriever, "retrieve", fake_retrieve)

    async def fake_recent(db_, session_id, limit):
        return []  # first message in the session — no prior history

    monkeypatch.setattr(chat_service, "_recent_messages", fake_recent)

    seen = {}

    async def fake_provider(system, prompt, temperature, max_tokens):
        seen["system"] = system
        seen["prompt"] = prompt
        return llm_service.LLMResult(text="It signs a JWT in auth_service.py.", input_tokens=200, output_tokens=20)

    monkeypatch.setitem(llm_service._PROVIDERS, "gemini", fake_provider)

    result = await chat_service.send_message(db, repo, session, "How does auth work?", cache=None)

    # both turns persisted
    assert result.user_message.role == "user"
    assert result.user_message.content == "How does auth work?"
    assert result.assistant_message.role == "assistant"
    assert result.assistant_message.content == "It signs a JWT in auth_service.py."
    assert result.user_message in db.added
    assert result.assistant_message in db.added

    # session gets an auto title from the first message
    assert session.title == "How does auth work?"

    # retrieved chunks are cited as sources on the assistant message
    assert result.sources == [
        {"file_path": c["file_path"], "start_line": c["start_line"],
         "end_line": c["end_line"], "language": c["language"], "score": c["score"]}
        for c in FAKE_CHUNKS
    ]
    assert result.assistant_message.sources == result.sources

    # the prompt actually grounds the model in the retrieved code
    assert "app/services/auth_service.py:39-42" in seen["prompt"]
    assert "How does auth work?" in seen["prompt"]
    assert seen["system"] == chat_service.SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_send_message_includes_prior_history(monkeypatch):
    _set_env(monkeypatch)
    from app.models.models import ChatSession, Message
    from app.rag import retriever
    from app.services import chat_service, llm_service

    repo = _make_repo()
    session = ChatSession(id=uuid.uuid4(), repo_id=repo.id, user_id=uuid.uuid4(), title="existing")
    db = FakeDB()

    prior = [
        Message(id=uuid.uuid4(), session_id=session.id, role="user", content="What does this repo do?"),
        Message(id=uuid.uuid4(), session_id=session.id, role="assistant", content="It's a dev workspace."),
    ]

    async def fake_recent(db_, session_id, limit):
        return prior

    monkeypatch.setattr(chat_service, "_recent_messages", fake_recent)
    monkeypatch.setattr(retriever, "retrieve", lambda *a, **kw: _async_return([]))

    seen = {}

    async def fake_provider(system, prompt, temperature, max_tokens):
        seen["prompt"] = prompt
        return llm_service.LLMResult(text="Follow-up answer.", input_tokens=10, output_tokens=5)

    monkeypatch.setitem(llm_service._PROVIDERS, "gemini", fake_provider)

    result = await chat_service.send_message(db, repo, session, "Tell me more", cache=None)

    # title untouched since the session already had one
    assert session.title == "existing"
    assert result.assistant_message.content == "Follow-up answer."
    # prior turns are folded into the prompt for continuity
    assert "Previous conversation" in seen["prompt"]
    assert "What does this repo do?" in seen["prompt"]
    assert "It's a dev workspace." in seen["prompt"]


async def _async_return(value):
    return value
