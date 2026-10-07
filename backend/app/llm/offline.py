"""A rule-based stand-in for the language model.

Used when no LLM key is configured (local development, CI, demos without
internet) and as the fallback if the real provider is down. It's not clever,
but it gives correct phonics help because it uses the same literacy engine
as the rest of the app, and it never makes anything up.
"""

from __future__ import annotations

import random
import re

from app.literacy.curriculum import PASSAGES
from app.literacy.decodability import analyze_word
from app.llm.base import ChatMessage

_QUOTED = re.compile(r"[\"'“”‘’]([A-Za-z]{2,30})[\"'“”‘’]")
_ASK_ABOUT = re.compile(
    r"\b(?:read|say|spell|split|sound out|pronounce|word)\s+(?:the\s+word\s+)?([A-Za-z]{2,30})\b", re.I
)
_STOP = {"the", "a", "an", "it", "this", "that", "word", "words", "me", "my", "please"}

_ENCOURAGEMENT = (
    "Nice work asking.",
    "Good question.",
    "Let's do it together.",
    "You've got this.",
)


def _find_word(text: str) -> str | None:
    for regex in (_QUOTED, _ASK_ABOUT):
        match = regex.search(text)
        if match and match.group(1).lower() not in _STOP:
            return match.group(1).lower()
    words = [w for w in re.findall(r"[A-Za-z]+", text) if w.lower() not in _STOP]
    if len(words) == 1:
        return words[0].lower()
    return None


class OfflineProvider:
    name = "offline"

    def __init__(self, seed: int | None = None) -> None:
        self._random = random.Random(seed)

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float = 0.6,
    ) -> str:
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")

        if "WRITE_PASSAGE" in (messages[0].content if messages else ""):
            return self._passage(messages)

        word = _find_word(last_user)
        if word:
            return self._explain_word(word)

        return (
            f"{self._random.choice(_ENCOURAGEMENT)} I can help you read or spell a word. "
            'Type the word in quotes, like "rabbit", and I\'ll break it into parts.'
        )

    def _explain_word(self, word: str) -> str:
        analysis = analyze_word(word)
        parts = [s.text for s in analysis.syllables]
        opener = self._random.choice(_ENCOURAGEMENT)

        if not parts:
            return f"{opener} I couldn't find that word. Can you type it again?"
        if analysis.required_level is None:
            return (
                f'{opener} "{word}" is a tricky word. It doesn\'t follow the usual rules, '
                "so we learn it by heart. Look at it, say it, then write it three times."
            )
        if len(parts) == 1:
            sounds = analysis.sound_count
            return (
                f'{opener} "{word}" has one syllable. '
                f"Tap your fingers for each sound. There are {sounds}. Then blend them together."
            )
        joined = "-".join(parts)
        return (
            f'{opener} "{word}" has {len(parts)} syllables: {joined}. '
            "Clap once for each part, read each part, then put them together."
        )

    def _passage(self, messages: list[ChatMessage]) -> str:
        # The reading service always verifies text, so returning a library
        # passage here keeps the offline path honest.
        level_match = re.search(r"LEVEL=(\d)", messages[0].content)
        level = int(level_match.group(1)) if level_match else 1
        title, text = PASSAGES.get(level, PASSAGES[1])
        return f"{title}\n{text}"
