from pydantic import BaseModel


class InterviewQuestionsResponse(BaseModel):
    questions: str
    tokens_used: int
    cached: bool
