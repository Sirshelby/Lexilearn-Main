from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.literacy.curriculum import LEVEL_TITLES, skills_for_level
from app.literacy.decodability import analyze_text, analyze_word
from app.schemas.literacy import (
    AnalyzeWordRequest,
    CheckTextOut,
    CheckTextRequest,
    CurriculumOut,
    LevelOut,
    SyllableOut,
    WordAnalysisOut,
    WordResultOut,
)
from app.services.progress import skill_out

router = APIRouter(tags=["literacy"])


@router.get("/curriculum", response_model=CurriculumOut)
async def curriculum() -> CurriculumOut:
    return CurriculumOut(
        levels=[
            LevelOut(level=level, title=title, skills=[skill_out(s) for s in skills_for_level(level)])
            for level, title in LEVEL_TITLES.items()
        ]
    )


@router.post("/literacy/analyze-word", response_model=WordAnalysisOut)
async def analyze(body: AnalyzeWordRequest, _: CurrentUser) -> WordAnalysisOut:
    a = analyze_word(body.word)
    return WordAnalysisOut(
        word=a.word,
        syllables=[SyllableOut(text=s.text, type=s.type.value) for s in a.syllables],
        patterns=a.describe_patterns(),
        required_level=a.required_level,
        heart_word_level=a.heart_word_level,
        sound_count=a.sound_count,
        decodable=a.decodable_at(body.level) if body.level else None,
    )


@router.post("/literacy/check-text", response_model=CheckTextOut)
async def check_text(body: CheckTextRequest, _: CurrentUser) -> CheckTextOut:
    report = analyze_text(body.text, body.level)
    return CheckTextOut(
        level=report.level,
        score=report.score,
        band=report.band,
        total_words=report.total_words,
        decodable_words=report.decodable_words,
        tricky_words=list(report.tricky_words),
        words=[
            WordResultOut(
                word=w.word,
                decodable=w.decodable,
                required_level=w.required_level,
                is_heart_word=w.is_heart_word,
            )
            for w in report.words
        ],
    )
