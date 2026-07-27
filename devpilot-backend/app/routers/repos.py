import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.models.models import Repo, User
from app.rag import vectorstore
from app.schemas.repos import RepoConnectRequest, RepoOut
from app.services import repo_service
from app.services.github_service import GitHubError

router = APIRouter()


async def _get_owned_repo(repo_id: uuid.UUID, user: User, db: AsyncSession) -> Repo:
    try:
        return await repo_service.get_owned_repo(db, repo_id, user)
    except repo_service.RepoNotFoundError:
        raise HTTPException(404, "Repository not found")


@router.post("", response_model=RepoOut, status_code=202)
async def connect_repo(
    body: RepoConnectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Repo:
    try:
        return await repo_service.connect_repo(db, user, body.github_full_name)
    except GitHubError as exc:
        raise HTTPException(400, str(exc))


@router.get("", response_model=list[RepoOut])
async def list_repos(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Repo]:
    result = await db.execute(
        select(Repo).where(Repo.user_id == user.id).order_by(Repo.created_at.desc())
    )
    return list(result.scalars())


@router.get("/{repo_id}", response_model=RepoOut)
async def get_repo(
    repo_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Repo:
    return await _get_owned_repo(repo_id, user, db)


@router.post("/{repo_id}/reindex", response_model=RepoOut, status_code=202)
async def reindex(
    repo_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Repo:
    repo = await _get_owned_repo(repo_id, user, db)
    return await repo_service.reindex_repo(db, repo)


@router.delete("/{repo_id}", status_code=204)
async def delete_repo(
    repo_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    repo = await _get_owned_repo(repo_id, user, db)
    client = vectorstore.get_client()
    try:
        await vectorstore.delete_repo_vectors(client, str(repo.id))
    finally:
        await client.close()
    await db.delete(repo)
    await db.commit()
