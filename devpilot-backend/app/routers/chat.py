import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal, get_db, get_redis
from app.deps import get_current_user
from app.models.models import ChatSession, Repo, User
from app.schemas.chat import ChatRequest, ChatResponse, ChatSessionOut, MessageOut
from app.services import chat_service, repo_service

router = APIRouter()


@router.post("/repos/{repo_id}/chat", response_model=ChatResponse)
async def chat(
    repo_id: uuid.UUID,
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    try:
        repo = await repo_service.get_owned_repo(db, repo_id, user)
    except repo_service.RepoNotFoundError:
        raise HTTPException(404, "Repository not found")

    try:
        session = await chat_service.get_or_create_session(db, repo, user, body.session_id)
    except chat_service.ChatError as exc:
        raise HTTPException(404, str(exc))

    redis = get_redis()
    try:
        result = await chat_service.send_message(db, repo, session, body.message, cache=redis)
    except chat_service.ChatError as exc:
        raise HTTPException(409, str(exc))
    except Exception:
        raise HTTPException(502, "LLM provider request failed")
    finally:
        await redis.aclose()

    return ChatResponse(
        session=ChatSessionOut.model_validate(result.session),
        message=MessageOut.model_validate(result.assistant_message),
        sources=result.sources,
    )


@router.post("/repos/{repo_id}/chat/stream")
async def chat_stream(
    repo_id: uuid.UUID,
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    try:
        repo = await repo_service.get_owned_repo(db, repo_id, user)
    except repo_service.RepoNotFoundError:
        raise HTTPException(404, "Repository not found")

    if repo.index_status != "ready":
        raise HTTPException(409, f"Repository is not ready for chat (status: {repo.index_status})")

    try:
        session = await chat_service.get_or_create_session(db, repo, user, body.session_id)
    except chat_service.ChatError as exc:
        raise HTTPException(404, str(exc))

    repo_id_, session_id_ = repo.id, session.id

    async def event_stream():
        # The request-scoped `db` closes as soon as this endpoint function returns, which
        # happens before Starlette starts pulling from this generator — so DB work here
        # needs its own session, not the one injected via Depends(get_db).
        try:
            async with SessionLocal() as stream_db:
                stream_repo = await stream_db.get(Repo, repo_id_)
                stream_session = await stream_db.get(ChatSession, session_id_)
                async for event in chat_service.stream_message(
                    stream_db, stream_repo, stream_session, body.message
                ):
                    yield f"data: {json.dumps(event)}\n\n"
        except chat_service.ChatError as exc:
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"
        except Exception:
            yield f"data: {json.dumps({'type': 'error', 'detail': 'LLM provider request failed'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/repos/{repo_id}/sessions", response_model=list[ChatSessionOut])
async def list_sessions(
    repo_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    try:
        repo = await repo_service.get_owned_repo(db, repo_id, user)
    except repo_service.RepoNotFoundError:
        raise HTTPException(404, "Repository not found")
    return await chat_service.list_sessions(db, repo)


@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
async def session_messages(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    try:
        session = await chat_service.get_owned_session(db, session_id, user)
    except chat_service.ChatError:
        raise HTTPException(404, "Chat session not found")
    return await chat_service.get_session_messages(db, session)
