import uuid

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_send_message_persists_and_round_trips(db, monkeypatch):
    from app.models.models import Repo, User
    from app.rag import retriever
    from app.services import chat_service, llm_service

    user = User(id=uuid.uuid4(), github_id=42, username="anvika", github_token_enc="enc")
    db.add(user)
    await db.commit()

    repo = Repo(id=uuid.uuid4(), user_id=user.id, github_full_name="anvika/devpilot", index_status="ready")
    db.add(repo)
    await db.commit()

    session = await chat_service.get_or_create_session(db, repo, user, None)
    assert session.id is not None
    assert session.created_at is not None  # server_default actually fired

    async def fake_retrieve(repo_id, query, k=8):
        return [{
            "score": 0.9, "file_path": "app/main.py", "start_line": 1,
            "end_line": 5, "language": "python", "text": "app = FastAPI()",
        }]

    monkeypatch.setattr(retriever, "retrieve", fake_retrieve)

    async def fake_provider(system, prompt, temperature, max_tokens):
        return llm_service.LLMResult(text="This bootstraps the FastAPI app.", input_tokens=50, output_tokens=10)

    monkeypatch.setitem(llm_service._PROVIDERS, "gemini", fake_provider)

    result = await chat_service.send_message(db, repo, session, "What does main.py do?", cache=None)
    assert result.assistant_message.content == "This bootstraps the FastAPI app."

    # read-side queries need a real DB — this is exactly what the FakeDB
    # unit tests in test_chat_service.py can't exercise
    sessions = await chat_service.list_sessions(db, repo)
    assert len(sessions) == 1
    assert sessions[0].id == session.id
    assert sessions[0].title == "What does main.py do?"

    messages = await chat_service.get_session_messages(db, session)
    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[0].content == "What does main.py do?"
    assert messages[1].sources[0]["file_path"] == "app/main.py"
    assert messages[1].token_count == 60


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_or_create_session_persists_across_calls(db):
    from app.models.models import Repo, User
    from app.services import chat_service

    user = User(id=uuid.uuid4(), github_id=7, username="anvika", github_token_enc="enc")
    repo = Repo(id=uuid.uuid4(), user_id=user.id, github_full_name="anvika/devpilot", index_status="ready")
    db.add_all([user, repo])
    await db.commit()

    created = await chat_service.get_or_create_session(db, repo, user, None)
    fetched = await chat_service.get_or_create_session(db, repo, user, created.id)

    assert fetched.id == created.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_or_create_session_rejects_cross_repo_session(db):
    """A session created for one repo can't be reused against a different one."""
    from app.models.models import Repo, User
    from app.services import chat_service

    user = User(id=uuid.uuid4(), github_id=8, username="anvika", github_token_enc="enc")
    repo_a = Repo(id=uuid.uuid4(), user_id=user.id, github_full_name="anvika/repo-a", index_status="ready")
    repo_b = Repo(id=uuid.uuid4(), user_id=user.id, github_full_name="anvika/repo-b", index_status="ready")
    db.add_all([user, repo_a, repo_b])
    await db.commit()

    session = await chat_service.get_or_create_session(db, repo_a, user, None)

    with pytest.raises(chat_service.ChatError):
        await chat_service.get_or_create_session(db, repo_b, user, session.id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_deleting_repo_cascades_to_sessions_and_messages(db, monkeypatch):
    """Confirms the cascade="all, delete-orphan" relationships actually
    clean up chat history when a repo (or session) is deleted — this is
    exactly the kind of constraint a fake DB can't verify."""
    from sqlalchemy import select

    from app.models.models import ChatSession, Message, Repo, User
    from app.rag import retriever
    from app.services import chat_service, llm_service

    user = User(id=uuid.uuid4(), github_id=9, username="anvika", github_token_enc="enc")
    repo = Repo(id=uuid.uuid4(), user_id=user.id, github_full_name="anvika/devpilot", index_status="ready")
    db.add_all([user, repo])
    await db.commit()

    session = await chat_service.get_or_create_session(db, repo, user, None)

    monkeypatch.setattr(retriever, "retrieve", lambda *a, **kw: _immediate([]))

    async def fake_provider(system, prompt, temperature, max_tokens):
        return llm_service.LLMResult(text="ok", input_tokens=1, output_tokens=1)

    monkeypatch.setitem(llm_service._PROVIDERS, "gemini", fake_provider)
    await chat_service.send_message(db, repo, session, "hello", cache=None)

    await db.delete(repo)
    await db.commit()

    remaining_sessions = (await db.execute(select(ChatSession))).scalars().all()
    remaining_messages = (await db.execute(select(Message))).scalars().all()
    assert remaining_sessions == []
    assert remaining_messages == []


async def _immediate(value):
    return value
