"""Decodable passages for the reading room.

The language model writes a story, then the rule engine checks it. If the
story uses too many patterns the learner hasn't been taught, we try once more
and then fall back to a hand-written passage from the curriculum. The model
is never trusted to judge decodability itself.
"""

from __future__ import annotations

import logging

from app.literacy.curriculum import LEVEL_TITLES, PASSAGES, skills_for_level
from app.literacy.decodability import INDEPENDENT_THRESHOLD, analyze_text
from app.llm import ChatMessage, LLMError, LLMProvider
from app.llm.prompts import passage_prompt
from app.schemas.reading import PassageOut

log = logging.getLogger(__name__)

ATTEMPTS = 2


def _parse(raw: str) -> tuple[str, str] | None:
    lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    title = lines[0].strip('#*" ').rstrip(".")
    text = " ".join(lines[1:])
    if not (20 <= len(text.split()) <= 120):
        return None
    return title[:60], text


def library_passage(level: int) -> PassageOut:
    title, text = PASSAGES[level]
    report = analyze_text(text, level)
    return PassageOut(
        title=title,
        text=text,
        level=level,
        score=report.score,
        source="library",
        tricky_words=list(report.tricky_words),
    )


async def get_passage(level: int, topic: str | None, llm: LLMProvider) -> PassageOut:
    if topic is None or llm.name == "offline":
        return library_passage(level)

    words = [w for skill in skills_for_level(level) for w in skill.words][:16]
    prompt = [ChatMessage("system", passage_prompt(level, LEVEL_TITLES[level], words, topic))]

    for attempt in range(ATTEMPTS):
        try:
            raw = await llm.complete(prompt, max_tokens=250, temperature=0.8)
        except LLMError:
            break
        parsed = _parse(raw)
        if not parsed:
            continue
        title, text = parsed
        report = analyze_text(text, level)
        if report.score >= INDEPENDENT_THRESHOLD:
            return PassageOut(
                title=title,
                text=text,
                level=level,
                score=report.score,
                source="generated",
                tricky_words=list(report.tricky_words),
            )
        log.info("generated passage rejected (attempt %s, score %s)", attempt + 1, report.score)

    return library_passage(level)
