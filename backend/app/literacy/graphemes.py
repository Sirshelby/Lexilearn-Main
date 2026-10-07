"""
Splits a word into graphemes: the letter or group of letters that spell one sound.

Everything else in the literacy package (syllables, decodability, sound
counting) is built on top of this, so it's kept table-driven and boring on
purpose. The tables follow the order a structured literacy programme would
teach them, not a full phonetic model of English. English spelling has far
too many exceptions for a rule engine to be perfect, so the goal here is
"right for the words a beginner reader actually meets", and anything we
can't handle falls back to being treated as irregular.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

VOWEL_LETTERS = frozenset("aeiou")

# Longest patterns first so "eigh" wins over "ei", "tch" over "ch" etc.
VOWEL_TEAMS = (
    "eigh",
    "igh",
    "ai",
    "ay",
    "ee",
    "ea",
    "oa",
    "oe",
    "ue",
    "ew",
    "ie",
    "ei",
    "ey",
    "oo",
    "ow",
    "ui",
    "oi",
    "oy",
    "ou",
    "au",
    "aw",
)
# Diphthongs are vowel teams where the mouth moves during the sound. OG
# programmes usually teach them later, so they get their own pattern tag.
# "ow" is left out because it's ambiguous (snow vs cow).
DIPHTHONGS = frozenset({"oi", "oy", "ou", "au", "aw"})

TRIGRAPHS = ("tch", "dge")
DIGRAPHS = ("sh", "ch", "th", "wh", "ck", "qu")
WELDED = ("ng", "nk")  # "glued" sounds in OG terminology
ADVANCED_DIGRAPHS = ("ph", "kn", "wr", "gn", "mb", "gh")

# Spellings we know we can't sound out with the rules above.
IRREGULAR_CHUNKS = ("ough", "augh", "ould")


class Kind(StrEnum):
    CONSONANT = "consonant"
    DIGRAPH = "digraph"
    TRIGRAPH = "trigraph"
    WELDED = "welded"
    ADVANCED = "advanced"
    VOWEL = "vowel"
    VOWEL_TEAM = "vowel_team"
    R_CONTROLLED = "r_controlled"
    SILENT_E = "silent_e"
    IRREGULAR = "irregular"


NUCLEUS_KINDS = frozenset({Kind.VOWEL, Kind.VOWEL_TEAM, Kind.R_CONTROLLED})


@dataclass(frozen=True, slots=True)
class Grapheme:
    text: str
    kind: Kind
    start: int  # index of the first letter in the original word

    @property
    def is_nucleus(self) -> bool:
        """True if this grapheme carries the vowel sound of a syllable."""
        return self.kind in NUCLEUS_KINDS

    @property
    def is_consonant(self) -> bool:
        return not self.is_nucleus and self.kind is not Kind.SILENT_E


def _is_vowel_at(word: str, i: int) -> bool:
    """Vowel test that also handles y (consonant at the start, vowel elsewhere)."""
    ch = word[i]
    if ch in VOWEL_LETTERS:
        return True
    if ch == "y":
        return i > 0 and word[i - 1] not in VOWEL_LETTERS
    return False


def _match_any(word: str, i: int, options: tuple[str, ...]) -> str | None:
    for option in options:
        if word.startswith(option, i):
            return option
    return None


def split_ing(word: str) -> tuple[str, str]:
    """Separate an -ing suffix so the stem is parsed on its own.

    Without this, "going" parses as g-oi-ng (one syllable) because "oi"
    looks like a vowel team. Short words like "sing" and "thing" keep their
    ending because the stem has no vowel.
    """
    if word.endswith("ing") and len(word) > 4:
        stem = word[:-3]
        if any(_is_vowel_at(stem, i) for i in range(len(stem))):
            return stem, "ing"
    return word, ""


def parse_graphemes(word: str) -> list[Grapheme]:
    """Parse a lowercase, letters-only word into graphemes."""
    stem, suffix = split_ing(word)
    graphemes = _parse(stem)
    if suffix:
        offset = len(stem)
        graphemes += [Grapheme(g.text, g.kind, g.start + offset) for g in _parse(suffix)]
    return graphemes


def _parse(word: str) -> list[Grapheme]:
    """Greedy left-to-right parse of a single stem or suffix."""
    graphemes: list[Grapheme] = []
    i = 0
    n = len(word)

    while i < n:
        chunk = _match_any(word, i, IRREGULAR_CHUNKS)
        if chunk:
            graphemes.append(Grapheme(chunk, Kind.IRREGULAR, i))
            i += len(chunk)
            continue

        team = _match_any(word, i, VOWEL_TEAMS)
        # "ue" and "ie" at the very start are not teams in any common word,
        # and "ey"/"ay" etc. need the first letter to be a real vowel.
        if team and word[i] in VOWEL_LETTERS:
            graphemes.append(Grapheme(team, Kind.VOWEL_TEAM, i))
            i += len(team)
            continue

        if word[i] in VOWEL_LETTERS and i + 1 < n and word[i + 1] == "r":
            # Vowel + r is r-controlled unless the r starts the next syllable
            # (he-ro, ze-ro). "rr" still counts: car-rot, hur-ry.
            after = word[i + 2] if i + 2 < n else ""
            if not after or not _is_vowel_at(word, i + 2) or after == "r":
                graphemes.append(Grapheme(word[i : i + 2], Kind.R_CONTROLLED, i))
                i += 2
                continue

        for options, kind in (
            (TRIGRAPHS, Kind.TRIGRAPH),
            (DIGRAPHS, Kind.DIGRAPH),
            (ADVANCED_DIGRAPHS, Kind.ADVANCED),
        ):
            match = _match_any(word, i, options)
            if match:
                graphemes.append(Grapheme(match, kind, i))
                i += len(match)
                break
        else:
            welded = _match_any(word, i, WELDED)
            # ng/nk only behave as a unit after a vowel (ring, bank).
            if welded and graphemes and graphemes[-1].is_nucleus:
                graphemes.append(Grapheme(welded, Kind.WELDED, i))
                i += 2
                continue

            kind = Kind.VOWEL if _is_vowel_at(word, i) else Kind.CONSONANT
            graphemes.append(Grapheme(word[i], kind, i))
            i += 1

    return _mark_silent_e(word, graphemes)


# Endings where "-es" is its own syllable (box-es, wish-es, fac-es).
_SYLLABIC_ES_AFTER = frozenset({"s", "x", "z", "ch", "sh", "c", "g", "ss", "zz", "tch", "dge"})
# Words ending in -ed that are not past tense verbs.
_NOT_PAST_TENSE = frozenset(
    {
        "hundred",
        "sacred",
        "kindred",
        "naked",
        "wicked",
        "rugged",
        "crooked",
        "ragged",
        "jagged",
        "beloved",
        "shred",
        "sled",
        "bed",
        "red",
        "fed",
        "led",
        "wed",
        "shed",
        "bred",
        "fled",
        "sped",
        "bled",
        "need",
        "seed",
        "feed",
        "weed",
    }
)


def _mark_silent_e(word: str, graphemes: list[Grapheme]) -> list[Grapheme]:
    """Turn the right 'e' graphemes into SILENT_E.

    Handles final e (cake), consonant-le (table), -es (makes) and -ed
    (jumped). Only applies when the word has another vowel to lean on,
    otherwise words like "he" and "the" would lose their only vowel.
    """

    def has_nucleus_before(idx: int) -> bool:
        return any(g.is_nucleus for g in graphemes[:idx])

    def silence(idx: int) -> None:
        g = graphemes[idx]
        graphemes[idx] = Grapheme(g.text, Kind.SILENT_E, g.start)

    if not graphemes:
        return graphemes

    last = len(graphemes) - 1
    tail = graphemes[last]

    # cake, table, house, horse
    if tail.text == "e" and tail.kind is Kind.VOWEL and last >= 1:
        if graphemes[last - 1].is_consonant and has_nucleus_before(last - 1):
            silence(last)
        return graphemes

    if last >= 2 and graphemes[last - 1].text == "e" and graphemes[last - 1].kind is Kind.VOWEL:
        before = graphemes[last - 2]
        if not has_nucleus_before(last - 2) and before.is_consonant:
            return graphemes

        if tail.text == "s" and before.is_consonant and before.text not in _SYLLABIC_ES_AFTER:
            silence(last - 1)  # makes, hopes, rides
        elif (
            tail.text == "d"
            and before.text not in {"t", "d"}
            and word not in _NOT_PAST_TENSE
            and has_nucleus_before(last - 1)
        ):
            silence(last - 1)  # jumped, played, wished

    return graphemes
