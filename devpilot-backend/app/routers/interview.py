import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, get_redis
from app.deps import get_current_user
from app.models.models import User
from app.schemas.interview import InterviewQuestionsResponse
from app.services import interview_service, repo_service

router = APIRouter()


@router.post("/repos/{repo_id}/interview-questions", response_model=InterviewQuestionsResponse)
async def interview_questions(
    repo_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterviewQuestionsResponse:
    try:
        repo = await repo_service.get_owned_repo(db, repo_id, user)
    except repo_service.RepoNotFoundError:
        raise HTTPException(404, "Repository not found")

    if repo.index_status != "ready":
        raise HTTPException(409, f"Repository is not ready (status: {repo.index_status})")

    redis = get_redis()
    try:
        result = await interview_service.generate(str(repo.id), cache=redis)
    except Exception:
        raise HTTPException(502, "LLM provider request failed")
    finally:
        await redis.aclose()

    return InterviewQuestionsResponse(
        questions=result.text,
        tokens_used=result.total_tokens,
        cached=result.cached,
    )
