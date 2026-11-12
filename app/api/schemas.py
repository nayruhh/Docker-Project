"""Request/response validation models."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

MAX_QUESTION_LENGTH = 2000


class AskRequest(BaseModel):
    # strip_whitespace runs before the length checks, so "   " is rejected as empty
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    question: str = Field(
        ...,
        min_length=1,
        max_length=MAX_QUESTION_LENGTH,
        description="The question to ask the model.",
        examples=["What is the capital of France?"],
    )


class AskResponse(BaseModel):
    answer: str


class HistoryItem(BaseModel):
    id: uuid.UUID
    question: str
    answer: str
    cache_hit: bool
    created_at: datetime
