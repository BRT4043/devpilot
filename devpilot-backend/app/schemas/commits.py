from pydantic import BaseModel, Field


class CommitMessageRequest(BaseModel):
    diff: str = Field(min_length=1, max_length=200_000)
    style: str = "conventional"


class CommitMessageResponse(BaseModel):
    message: str
    tokens_used: int
    cached: bool
