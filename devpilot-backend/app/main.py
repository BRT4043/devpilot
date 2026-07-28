import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _run_migrations() -> None:
    """Runs synchronously; Alembic's own env.py calls asyncio.run() internally,
    so this must execute off the event loop thread (see call site)."""
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config("alembic.ini"), "head")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "startup flags: run_migrations_on_startup=%r run_worker_in_process=%r",
        settings.run_migrations_on_startup,
        settings.run_worker_in_process,
    )
    if settings.run_migrations_on_startup:
        logger.info("running alembic upgrade head...")
        try:
            await asyncio.to_thread(_run_migrations)
            logger.info("alembic upgrade head: done")
        except Exception:
            logger.exception("alembic upgrade head FAILED")

    worker_task: asyncio.Task | None = None
    if settings.run_worker_in_process:
        from arq.worker import create_worker

        from app.workers.indexing_worker import WorkerSettings

        worker = create_worker(WorkerSettings)
        worker_task = asyncio.create_task(worker.async_run())

    yield

    if worker_task is not None:
        worker_task.cancel()


app = FastAPI(
    title="DevPilot AI",
    version="0.1.0",
    description="AI developer workspace that understands your GitHub repository.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "env": settings.app_env}


from app.routers import auth, chat, commits, debug, explain, github, interview, repos  # noqa: E402

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(commits.router, tags=["commits"])
app.include_router(repos.router, prefix="/repos", tags=["repos"])
app.include_router(chat.router, tags=["chat"])
app.include_router(explain.router, tags=["explain"])
app.include_router(debug.router, tags=["debug"])
app.include_router(interview.router, tags=["interview"])
app.include_router(github.router, tags=["github"])
