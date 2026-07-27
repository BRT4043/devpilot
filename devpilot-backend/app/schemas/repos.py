import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RepoConnectRequest(BaseModel):
    github_full_name: str = Field(pattern=r"^[\w.\-]+/[\w.\-]+$", examples=["anvika/chargehub"])


class RepoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    github_full_name: str
    default_branch: str
    index_status: str
    index_error: str | None = None
    indexed_commit_sha: str | None = None
    file_count: int | None = None
    chunk_count: int | None = None
    created_at: datetime
