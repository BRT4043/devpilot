from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_current_user
from app.models.models import User
from app.services import auth_service, github_service

router = APIRouter()


@router.get("/github/repos")
async def list_my_github_repos(user: User = Depends(get_current_user)) -> list[dict]:
    token = auth_service.decrypt_token(user.github_token_enc)
    try:
        return await github_service.list_user_repos(token)
    except Exception:
        raise HTTPException(502, "Could not fetch your GitHub repositories")
