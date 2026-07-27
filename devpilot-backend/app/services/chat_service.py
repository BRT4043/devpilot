"""Repo-aware chat: retrieve context, build a grounded prompt, call the LLM,
and persist the conversation.
"""

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import ChatSession, Message, Repo, User
from app.rag import retriever
from app.services import llm_service

TOP_K = 8
HISTORY_MESSAGES = 6  # last N messages (≈3 turns) fed back in as conversation context
MAX_CONTEXT_CHARS = 12_000  # keep the retrieved-chunk block bounded
TITLE_CHARS = 80

SYSTEM_PROMPT = (
    "You are DevPilot, a friendly assistant that explains a GitHub repository in "
    "plain, everyday language — like explaining it to a smart colleague who hasn't "
    "seen the code yet, not writing documentation. Avoid unnecessary jargon; if you "
    "must use a technical term, briefly say what it means. Answer only what was "
    "asked — stay short and focused, don't dump unrelated implementation details "
    "just because they're in the context. You are given code excerpts retrieved "
    "from the repository as grounding; use them to make sure you're right, and "
    "mention a specific file only when it genuinely helps the reader. If the "
    "context doesn't contain enough information to answer confidently, say so "
    "plainly instead of guessing. When a diagram would genuinely make the answer "
    "clearer — an architecture overview, a request flow, a sequence of steps — "
    "include one as a fenced ```mermaid code block using Mermaid syntax. Don't "
    "force a diagram into answers that don't need one.\n\n"
    "When the user asks you to build, add, or implement something non-trivial "
    "(a new feature, endpoint, screen, or integration) rather than just asking a "
    "question — act like a thoughtful tech lead, not a code-generator. If the "
    "request is genuinely underspecified in a way that would change the design "
    "(e.g. scale, auth requirements, which existing pattern to follow, data "
    "storage) and the repository context doesn't already answer it, ask 2-4 "
    "short clarifying questions before proposing anything — don't ask about "
    "things you can already tell from the codebase. Once you have enough to go "
    "on, respond with a short structured plan: what it affects, how it fits the "
    "existing architecture and conventions in this repo, the concrete steps, and "
    "anything risky — before diving into actual code."
)


class ChatError(Exception):
    """Raised when a chat request can't be served (bad session, repo not ready, ...)."""


@dataclass
class ChatResult:
    session: ChatSession
    user_message: Message
    assistant_message: Message
    sources: list[dict]


def _format_context(chunks: list[dict]) -> str:
    if not chunks:
        return "(No relevant code was found in the repository for this question.)"
    blocks = []
    total = 0
    for c in chunks:
        header = f"### {c['file_path']}:{c['start_line']}-{c['end_line']} ({c['language']})"
        block = f"{header}\n```{c['language']}\n{c['text']}\n```"
        if blocks and total + len(block) > MAX_CONTEXT_CHARS:
            break
        blocks.append(block)
        total += len(block)
    return "\n\n".join(blocks)


def _format_history(history: list[Message]) -> str:
    if not history:
        return ""
    lines = [f"{m.role.capitalize()}: {m.content}" for m in history]
    return "Previous conversation:\n" + "\n".join(lines) + "\n\n"


def _extract_sources(chunks: list[dict]) -> list[dict]:
    return [
        {
            "file_path": c["file_path"],
            "start_line": c["start_line"],
            "end_line": c["end_line"],
            "language": c["language"],
            "score": c["score"],
        }
        for c in chunks
    ]


async def _recent_messages(db: AsyncSession, session_id: uuid.UUID, limit: int) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


async def get_or_create_session(
    db: AsyncSession, repo: Repo, user: User, session_id: uuid.UUID | None
) -> ChatSession:
    """Fetch an existing session (verifying ownership) or start a new one."""
    if session_id is not None:
        session = await db.get(ChatSession, session_id)
        if session is None or session.repo_id != repo.id or session.user_id != user.id:
            raise ChatError("Chat session not found")
        return session

    session = ChatSession(repo_id=repo.id, user_id=user.id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_owned_session(db: AsyncSession, session_id: uuid.UUID, user: User) -> ChatSession:
    """Fetch a session by id, verifying it belongs to the user."""
    session = await db.get(ChatSession, session_id)
    if session is None or session.user_id != user.id:
        raise ChatError("Chat session not found")
    return session


async def send_message(
    db: AsyncSession,
    repo: Repo,
    session: ChatSession,
    content: str,
    cache: Redis | None = None,
) -> ChatResult:
    if repo.index_status != "ready":
        raise ChatError(f"Repository is not ready for chat (status: {repo.index_status})")

    history = await _recent_messages(db, session.id, HISTORY_MESSAGES)

    user_message = Message(session_id=session.id, role="user", content=content)
    db.add(user_message)
    await db.commit()
    await db.refresh(user_message)

    if session.title is None:
        session.title = content[:TITLE_CHARS]

    chunks = await retriever.retrieve(str(repo.id), content, k=TOP_K)

    prompt = (
        f"{_format_history(history)}"
        f"Repository context:\n{_format_context(chunks)}\n\n"
        f"Question: {content}"
    )
    result = await llm_service.complete(prompt, system=SYSTEM_PROMPT, cache=cache)
    sources = _extract_sources(chunks)

    assistant_message = Message(
        session_id=session.id,
        role="assistant",
        content=result.text,
        sources=sources,
        token_count=result.total_tokens,
    )
    db.add(assistant_message)
    await db.commit()
    await db.refresh(assistant_message)

    return ChatResult(
        session=session,
        user_message=user_message,
        assistant_message=assistant_message,
        sources=sources,
    )


async def stream_message(
    db: AsyncSession,
    repo: Repo,
    session: ChatSession,
    content: str,
) -> AsyncIterator[dict]:
    """Same as send_message but yields incremental events as the answer streams in:
    {"type": "meta", ...} once, then {"type": "chunk", "text": ...} repeatedly,
    then {"type": "done", ...} once.
    """
    if repo.index_status != "ready":
        raise ChatError(f"Repository is not ready for chat (status: {repo.index_status})")

    history = await _recent_messages(db, session.id, HISTORY_MESSAGES)

    user_message = Message(session_id=session.id, role="user", content=content)
    db.add(user_message)
    await db.commit()
    await db.refresh(user_message)

    if session.title is None:
        session.title = content[:TITLE_CHARS]
        await db.commit()
        await db.refresh(session)

    chunks = await retriever.retrieve(str(repo.id), content, k=TOP_K)
    sources = _extract_sources(chunks)
    prompt = (
        f"{_format_history(history)}"
        f"Repository context:\n{_format_context(chunks)}\n\n"
        f"Question: {content}"
    )

    yield {
        "type": "meta",
        "session_id": str(session.id),
        "session_title": session.title,
        "sources": sources,
    }

    full_text = ""
    input_tokens = output_tokens = 0
    async for piece in llm_service.stream_complete(prompt, system=SYSTEM_PROMPT):
        if piece.done:
            input_tokens, output_tokens = piece.input_tokens, piece.output_tokens
            continue
        full_text += piece.text
        yield {"type": "chunk", "text": piece.text}

    assistant_message = Message(
        session_id=session.id,
        role="assistant",
        content=full_text,
        sources=sources,
        token_count=input_tokens + output_tokens,
    )
    db.add(assistant_message)
    await db.commit()
    await db.refresh(assistant_message)

    yield {
        "type": "done",
        "message_id": str(assistant_message.id),
        "token_count": assistant_message.token_count,
        "created_at": assistant_message.created_at.isoformat(),
    }


async def list_sessions(db: AsyncSession, repo: Repo) -> list[ChatSession]:
    result = await db.execute(
        select(ChatSession).where(ChatSession.repo_id == repo.id).order_by(ChatSession.created_at.desc())
    )
    return list(result.scalars())


async def get_session_messages(db: AsyncSession, session: ChatSession) -> list[Message]:
    result = await db.execute(
        select(Message).where(Message.session_id == session.id).order_by(Message.created_at.asc())
    )
    return list(result.scalars())
