import uuid
from typing import Literal

from pydantic import BaseModel, Field

ItemKind = Literal["listen_choose", "spell", "count_sounds", "split_syllables"]


class StartPracticeRequest(BaseModel):
    skill_code: str | None = Field(default=None, max_length=8)


class PracticeItemOut(BaseModel):
    index: int
    kind: ItemKind
    prompt: str
    # Text the client should read aloud for listening items. Grading is still
    # done on the server; see models.progress.PracticeSession.
    say: str | None = None
    word: str | None = None  # shown on screen (count_sounds, split_syllables)
    choices: list[str] | None = None


class PracticeSessionOut(BaseModel):
    id: uuid.UUID
    skill_code: str
    skill_title: str
    tip: str
    items: list[PracticeItemOut]


class AnswerRequest(BaseModel):
    item_index: int = Field(ge=0)
    answer: str = Field(max_length=60)


class AnswerResult(BaseModel):
    correct: bool
    expected: str
    feedback: str
    syllables: list[str] | None = None


class CompleteResult(BaseModel):
    skill_code: str
    correct: int
    total: int
    accuracy: float
    mastered_now: bool
    skill_status: str
    next_skill_code: str | None
