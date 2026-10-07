from pydantic import BaseModel, Field


class PassageRequest(BaseModel):
    topic: str | None = Field(default=None, max_length=60)
    level: int | None = Field(default=None, ge=1, le=8)


class PassageOut(BaseModel):
    title: str
    text: str
    level: int
    score: float
    source: str  # "generated" or "library"
    tricky_words: list[str]
