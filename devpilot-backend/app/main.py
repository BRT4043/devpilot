import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
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
