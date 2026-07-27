"""Background worker: full repo indexing pipeline.

Run with:  arq app.workers.indexing_worker.WorkerSettings
"""

import uuid

from arq.connections import RedisSettings
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models.models import Repo, User
from app.rag import chunking, embeddings, ingestion, vectorstore
from app.services import auth_service, github_service

settings = get_settings()


async def index_repo(ctx: dict, repo_id: str) -> str:
    async with SessionLocal() as db:
        repo = await db.get(Repo, uuid.UUID(repo_id))
        if repo is None:
            return f"repo {repo_id} not found"
        user = await db.get(User, repo.user_id)

        repo.index_status = "indexing"
        repo.index_error = None
        await db.commit()

        clone_path = None
        client = None
        try:
            token = auth_service.decrypt_token(user.github_token_enc)
            sha = await github_service.get_head_sha(token, repo.github_full_name, repo.default_branch)
            clone_path = await github_service.shallow_clone(
                token, repo.github_full_name, repo.default_branch
            )

            files = ingestion.collect_files(clone_path)
            chunks = chunking.split_files(files)
            if not chunks:
                raise ValueError("No indexable source files found in repository")

            vectors = await embeddings.embed_batch([c.text for c in chunks])

            client = vectorstore.get_client()
            await vectorstore.ensure_collection(client, vector_size=len(vectors[0]))
            # re-index safely: wipe old vectors first
            await vectorstore.delete_repo_vectors(client, repo_id)
            await vectorstore.upsert_chunks(client, repo_id, chunks, vectors)

            repo.index_status = "ready"
            repo.indexed_commit_sha = sha
            repo.file_count = len(files)
            repo.chunk_count = len(chunks)
            await db.commit()
            return f"indexed {repo.github_full_name}: {len(files)} files, {len(chunks)} chunks"

        except Exception as exc:
            repo.index_status = "failed"
            repo.index_error = str(exc)[:1000]
            await db.commit()
            raise
        finally:
            if clone_path is not None:
                github_service.cleanup_clone(clone_path)
            if client is not None:
                await client.close()


class WorkerSettings:
    functions = [index_repo]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 2
    job_timeout = 1800
