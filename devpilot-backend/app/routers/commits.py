from fastapi import APIRouter, Depends, HTTPException

from app.db import get_redis
from app.deps import get_current_user
from app.models.models import User
from app.schemas.commits import CommitMessageRequest, CommitMessageResponse
from app.services import commit_service

router = APIRouter()


@router.post("/commit-message", response_model=CommitMessageResponse)
async def commit_message(
    body: CommitMessageRequest,
    user: User = Depends(get_current_user),
) -> CommitMessageResponse:
    redis = get_redis()
    try:
        result = await commit_service.generate(body.diff, body.style, cache=redis)
    except Exception:
        raise HTTPException(502, "LLM provider request failed")
    finally:
        await redis.aclose()

    return CommitMessageResponse(
        message=result.text,
        tokens_used=result.total_tokens,
        cached=result.cached,
    )
