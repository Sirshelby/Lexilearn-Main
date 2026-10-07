"""Builds practice sessions from the curriculum and grades answers.

Each session mixes a few kinds of item so the same words are met through
different senses (hearing, spelling, counting sounds, seeing syllables),
which is the multisensory part of the approach.
"""

from __future__ import annotations

import random
from typing import Any

from app.literacy.curriculum import Skill
from app.literacy.decodability import analyze_word
from app.literacy.syllables import split_syllables
from app.schemas.practice import AnswerResult, PracticeItemOut

ITEMS_PER_SESSION = 8

PROMPTS = {
    "listen_choose": "Listen, then pick the word you hear.",
    "spell": "Listen, then spell the word.",
    "count_sounds": "How many sounds are in this word?",
    "split_syllables": "Tap between the letters to split the word into syllables.",
}


def _kinds_for(skill: Skill) -> list[str]:
    if skill.level <= 4:
        return ["listen_choose", "count_sounds", "spell"]
    return ["listen_choose", "split_syllables", "spell"]


def _make_item(kind: str, word: str, skill: Skill, rng: random.Random) -> dict[str, Any]:
    item: dict[str, Any] = {"kind": kind, "word": word, "prompt": PROMPTS[kind]}

    if kind == "listen_choose":
        others = [w for w in skill.words if w != word]
        choices = [word, *rng.sample(others, k=min(3, len(others)))]
        rng.shuffle(choices)
        item.update(say=word, choices=choices, answer=word)
    elif kind == "spell":
        item.update(say=word, answer=word)
    elif kind == "count_sounds":
        count = analyze_word(word).sound_count or len(word)
        options = sorted({max(1, count - 1), count, count + 1, count + 2})
        item.update(choices=[str(n) for n in options], answer=str(count))
    elif kind == "split_syllables":
        item.update(answer="-".join(split_syllables(word)))
    return item


def build_items(skill: Skill, rng: random.Random | None = None) -> list[dict[str, Any]]:
    rng = rng or random.Random()
    words = list(skill.words)
    rng.shuffle(words)
    kinds = _kinds_for(skill)

    items: list[dict[str, Any]] = []
    for i in range(ITEMS_PER_SESSION):
        word = words[i % len(words)]
        kind = kinds[i % len(kinds)]
        # Splitting a one-syllable word isn't a real question.
        if kind == "split_syllables" and len(split_syllables(word)) < 2:
            kind = "listen_choose"
        items.append(_make_item(kind, word, skill, rng))
    return items


def public_item(index: int, item: dict[str, Any]) -> PracticeItemOut:
    """What the browser is allowed to see before answering."""
    shows_word = item["kind"] in {"count_sounds", "split_syllables"}
    return PracticeItemOut(
        index=index,
        kind=item["kind"],
        prompt=item["prompt"],
        say=item.get("say"),
        word=item["word"] if shows_word else None,
        choices=item.get("choices"),
    )


def _normalise(text: str) -> str:
    return "".join(text.lower().split())


def grade(item: dict[str, Any], answer: str) -> AnswerResult:
    word: str = item["word"]
    expected: str = item["answer"]
    given = _normalise(answer)
    correct = given == _normalise(expected)
    syllables = split_syllables(word)

    if correct:
        feedback = {
            "listen_choose": "Yes! You heard it.",
            "spell": "Spot on. Every letter is right.",
            "count_sounds": f"Yes, {word} has {expected} sounds.",
            "split_syllables": f"Great splitting: {expected}.",
        }[item["kind"]]
    else:
        feedback = {
            "listen_choose": f"This one was {word}. Say it slowly and listen to each sound.",
            "spell": f"Nearly. It's spelled {'-'.join(word)}. Say each letter as you trace it.",
            "count_sounds": f"{word} has {expected} sounds. Tap one finger for each.",
            "split_syllables": f"It splits like this: {expected}. Find the vowels first.",
        }[item["kind"]]

    return AnswerResult(correct=correct, expected=expected, feedback=feedback, syllables=syllables)
