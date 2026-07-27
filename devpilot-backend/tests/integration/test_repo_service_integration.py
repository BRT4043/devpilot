import uuid

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_owned_repo_returns_repo_for_owner(db):
    from app.models.models import Repo, User
    from app.services import repo_service

    user = User(id=uuid.uuid4(), github_id=1, username="anvika", github_token_enc="enc")
    repo = Repo(id=uuid.uuid4(), user_id=user.id, github_full_name="anvika/devpilot", index_status="ready")
    db.add_all([user, repo])
    await db.commit()

    found = await repo_service.get_owned_repo(db, repo.id, user)
    assert found.id == repo.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_owned_repo_rejects_other_users_repo(db):
    from app.models.models import Repo, User
    from app.services import repo_service

    owner = User(id=uuid.uuid4(), github_id=1, username="anvika", github_token_enc="enc")
    intruder = User(id=uuid.uuid4(), github_id=2, username="someone-else", github_token_enc="enc")
    repo = Repo(id=uuid.uuid4(), user_id=owner.id, github_full_name="anvika/devpilot", index_status="ready")
    db.add_all([owner, intruder, repo])
    await db.commit()

    with pytest.raises(repo_service.RepoNotFoundError):
        await repo_service.get_owned_repo(db, repo.id, intruder)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_owned_repo_rejects_unknown_id(db):
    from app.models.models import User
    from app.services import repo_service

    user = User(id=uuid.uuid4(), github_id=1, username="anvika", github_token_enc="enc")
    db.add(user)
    await db.commit()

    with pytest.raises(repo_service.RepoNotFoundError):
        await repo_service.get_owned_repo(db, uuid.uuid4(), user)
