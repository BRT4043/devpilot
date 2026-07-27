from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    jwt_secret: str
    jwt_expire_minutes: int = 10080
    frontend_url: str = "http://localhost:3000"

    token_encryption_key: str

    github_client_id: str
    github_client_secret: str
    github_callback_url: str

    database_url: str
    redis_url: str
    qdrant_url: str
    qdrant_api_key: str = ""  # required for Qdrant Cloud, empty for local self-hosted

    @field_validator("database_url")
    @classmethod
    def _use_asyncpg_driver(cls, v: str) -> str:
        # Managed Postgres providers (Render, etc.) hand out a plain postgresql://
        # URL; SQLAlchemy's async engine needs the asyncpg dialect explicitly.
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # When true, the API process also runs the ARQ indexing worker in-process
    # (asyncio task) instead of relying on a separate worker service — needed
    # on hosts whose free tier doesn't offer a background-worker service type.
    run_worker_in_process: bool = False

    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.0-flash"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-004"
    llm_cache_ttl_seconds: int = 86400


@lru_cache
def get_settings() -> Settings:
    return Settings()
