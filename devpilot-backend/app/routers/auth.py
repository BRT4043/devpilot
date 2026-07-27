from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models.models import User
from app.schemas.auth import UserOut
from app.services import auth_service

settings = get_settings()
router = APIRouter()


@router.get("/github/login")
async def github_login() -> RedirectResponse:
    return RedirectResponse(auth_service.github_login_url())


@router.get("/github/callback")
async def github_callback(code: str, db: AsyncSession = Depends(get_db)) -> RedirectResponse:
    try:
        access_token = await auth_service.exchange_code_for_token(code)
        gh_user = await auth_service.fetch_github_user(access_token)
    except Exception:
        raise HTTPException(502, "GitHub OAuth exchange failed")

    user = await auth_service.upsert_user(db, gh_user, access_token)
    jwt_token = auth_service.create_jwt(user.id)
    # Frontend route /auth/callback reads ?token= and stores it
    return RedirectResponse(f"{settings.frontend_url}/auth/callback?token={jwt_token}")


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
