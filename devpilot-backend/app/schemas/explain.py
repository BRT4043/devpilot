from pydantic import BaseModel, Field

from app.schemas.chat import SourceOut


class ExplainRequest(BaseModel):
    code: str = Field(min_length=1, max_length=20_000)
    file_path: str | None = None
    language: str | None = None


class ExplainResponse(BaseModel):
    explanation: str
    sources: list[SourceOut]
    tokens_used: int
    cached: bool
