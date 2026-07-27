from functools import lru_cache

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

    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.0-flash"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-004"
    llm_cache_ttl_seconds: int = 86400


@lru_cache
def get_settings() -> Settings:
    return Settings()
