"""Connect repos and enqueue indexing jobs."""

import uuid

from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.models import Repo, User
from app.services import auth_service, github_service

settings = get_settings()


class RepoNotFoundError(Exception):
    """Raised when a repo doesn't exist or doesn't belong to the requesting user."""


async def get_owned_repo(db: AsyncSession, repo_id: uuid.UUID, user: User) -> Repo:
    """Fetch a repo by id, verifying it belongs to the user. Shared by any
    router/service that needs to scope work to a repo the user actually owns."""
    repo = await db.get(Repo, repo_id)
    if repo is None or repo.user_id != user.id:
        raise RepoNotFoundError("Repository not found")
    return repo


async def _enqueue_indexing(repo_id: uuid.UUID) -> None:
    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        await pool.enqueue_job("index_repo", repo_id=str(repo_id))
    finally:
        await pool.aclose()


async def connect_repo(db: AsyncSession, user: User, full_name: str) -> Repo:
    token = auth_service.decrypt_token(user.github_token_enc)
    info = await github_service.get_repo_info(token, full_name)  # raises if no access

    result = await db.execute(
        select(Repo).where(Repo.user_id == user.id, Repo.github_full_name == info["full_name"])
    )
    repo = result.scalar_one_or_none()
    if repo is None:
        repo = Repo(
            user_id=user.id,
            github_full_name=info["full_name"],
            default_branch=info["default_branch"],
            index_status="pending",
        )
        db.add(repo)
    else:
        repo.index_status = "pending"
        repo.index_error = None
    await db.commit()
    await db.refresh(repo)

    await _enqueue_indexing(repo.id)
    return repo


async def reindex_repo(db: AsyncSession, repo: Repo) -> Repo:
    repo.index_status = "pending"
    repo.index_error = None
    await db.commit()
    await _enqueue_indexing(repo.id)
    return repo
