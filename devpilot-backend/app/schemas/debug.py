from pydantic import BaseModel, Field

from app.schemas.chat import SourceOut


class DebugRequest(BaseModel):
    error_text: str = Field(min_length=1, max_length=6_000)


class DebugResponse(BaseModel):
    analysis: str
    sources: list[SourceOut]
    tokens_used: int
    cached: bool
