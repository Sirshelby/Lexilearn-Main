from pydantic import BaseModel, Field


class AnalyzeWordRequest(BaseModel):
    word: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z']+$")
    level: int | None = Field(default=None, ge=1, le=8)


class SyllableOut(BaseModel):
    text: str
    type: str


class WordAnalysisOut(BaseModel):
    word: str
    syllables: list[SyllableOut]
    patterns: list[str]
    required_level: int | None
    heart_word_level: int | None
    sound_count: int | None
    decodable: bool | None = None  # only set when a level was given


class CheckTextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    level: int = Field(ge=1, le=8)


class WordResultOut(BaseModel):
    word: str
    decodable: bool
    required_level: int | None
    is_heart_word: bool


class CheckTextOut(BaseModel):
    level: int
    score: float
    band: str
    total_words: int
    decodable_words: int
    tricky_words: list[str]
    words: list[WordResultOut]


class SkillOut(BaseModel):
    code: str
    level: int
    title: str
    focus: str
    tip: str
    words: list[str]


class LevelOut(BaseModel):
    level: int
    title: str
    skills: list[SkillOut]


class CurriculumOut(BaseModel):
    levels: list[LevelOut]
