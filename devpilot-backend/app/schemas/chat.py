import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8_000)
    session_id: uuid.UUID | None = None


class SourceOut(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    language: str
    score: float


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    sources: list[SourceOut] | None = None
    token_count: int | None = None
    created_at: datetime


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repo_id: uuid.UUID
    title: str | None = None
    created_at: datetime


class ChatResponse(BaseModel):
    session: ChatSessionOut
    message: MessageOut
    sources: list[SourceOut]
