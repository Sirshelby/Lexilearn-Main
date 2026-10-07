"""
Syllable division and syllable types.

This follows the division rules taught in Orton-Gillingham style programmes:

    VC/CV    rab-bit, nap-kin        split between two consonants
    V/CV     ro-bot, ti-ger          one consonant: try the open syllable first
    VC/V     cab-in, rock-et         ...unless that doesn't make a real word
    V/V      li-on                   two vowels that aren't a team
    VCCCV    hun-dred, pump-kin      keep a blend together if there is one
    C-le     ta-ble, lit-tle         consonant + le is its own syllable

Suffixes are split off first (jump-ing, want-ed) because that's how learners
are taught to see them, and it avoids a few silly results like "jum-ping".

The one rule a computer can't really apply is VC/V, because it depends on
whether the open version is a real word. Instead of shipping a dictionary I
keep a short list of common VC/V words. It's a known limitation and it's
written down in docs/ARCHITECTURE.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from itertools import pairwise

from app.literacy.graphemes import Grapheme, Kind, parse_graphemes, split_ing


class SyllableType(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    VCE = "vce"
    VOWEL_TEAM = "vowel_team"
    R_CONTROLLED = "r_controlled"
    CONSONANT_LE = "consonant_le"
    IRREGULAR = "irregular"


@dataclass(frozen=True, slots=True)
class Syllable:
    text: str
    type: SyllableType
    graphemes: tuple[Grapheme, ...]


BLENDS = frozenset(
    {
        "bl",
        "br",
        "cl",
        "cr",
        "dr",
        "fl",
        "fr",
        "gl",
        "gr",
        "pl",
        "pr",
        "sc",
        "sk",
        "sl",
        "sm",
        "sn",
        "sp",
        "st",
        "sw",
        "tr",
        "tw",
    }
)
FLOSS_LETTERS = frozenset("flsz")

# Common words where the first syllable is closed even though there's only
# one consonant between the vowels (VC/V).
VC_V_WORDS = frozenset(
    {
        "cabin",
        "robin",
        "lemon",
        "seven",
        "river",
        "never",
        "visit",
        "planet",
        "finish",
        "limit",
        "habit",
        "panic",
        "comic",
        "metal",
        "model",
        "salad",
        "timid",
        "wagon",
        "camel",
        "linen",
        "melon",
        "clever",
        "shiver",
        "liver",
        "solid",
        "rapid",
        "vivid",
        "lizard",
        "dragon",
        "travel",
        "level",
        "novel",
        "radish",
        "relish",
        "punish",
        "vanish",
        "denim",
        "credit",
        "edit",
        "tonic",
        "topic",
        "magic",
        "logic",
        "second",
        "proper",
        "copy",
        "body",
        "city",
        "very",
        "many",
        "money",
        "honey",
        "lily",
        "pity",
        "petal",
        "medal",
        "rivet",
        "closet",
        "present",
        "project",
        "eleven",
        "cover",
        "oven",
        "shovel",
        "gravel",
        "tepid",
        "valid",
        "vomit",
    }
)

# Words the rules get wrong that come up often enough to be worth fixing.
OVERRIDES: dict[str, list[str]] = {
    "quiet": ["qui", "et"],
    "diet": ["di", "et"],
    "science": ["sci", "ence"],
    "create": ["cre", "ate"],
    "idea": ["i", "de", "a"],
    "poem": ["po", "em"],
    "poet": ["po", "et"],
    "react": ["re", "act"],
    "finger": ["fin", "ger"],
    "hunger": ["hun", "ger"],
    "anger": ["an", "ger"],
}


def _shift(graphemes: list[Grapheme], offset: int) -> list[Grapheme]:
    return [Grapheme(g.text, g.kind, g.start + offset) for g in graphemes]


def _classify(graphemes: list[Grapheme]) -> SyllableType:
    kinds = {g.kind for g in graphemes}
    if Kind.IRREGULAR in kinds:
        return SyllableType.IRREGULAR
    if Kind.R_CONTROLLED in kinds:
        return SyllableType.R_CONTROLLED
    if Kind.VOWEL_TEAM in kinds:
        return SyllableType.VOWEL_TEAM

    nucleus_positions = [i for i, g in enumerate(graphemes) if g.is_nucleus]
    if not nucleus_positions:
        return SyllableType.IRREGULAR
    v = nucleus_positions[-1]

    if Kind.SILENT_E in kinds:
        e = next(i for i, g in enumerate(graphemes) if g.kind is Kind.SILENT_E)
        between = graphemes[v + 1 : e]
        if len(between) == 1 and between[0].is_consonant:
            return SyllableType.VCE

    after_vowel = [g for g in graphemes[v + 1 :] if g.kind is not Kind.SILENT_E]
    return SyllableType.CLOSED if after_vowel else SyllableType.OPEN


def _cut_points(word: str, graphemes: list[Grapheme]) -> list[int]:
    """Grapheme indices where each new syllable starts."""
    nuclei = [i for i, g in enumerate(graphemes) if g.is_nucleus]
    cuts: list[int] = []

    for a, b in pairwise(nuclei):
        between = graphemes[a + 1 : b]
        n = len(between)

        if n == 0:  # V/V
            cut = b
        elif n == 1:
            g = between[0]
            closes_syllable = (
                g.kind in {Kind.DIGRAPH, Kind.TRIGRAPH, Kind.WELDED, Kind.ADVANCED} and g.text != "qu"
            ) or g.text == "x"
            cut = b if closes_syllable or word in VC_V_WORDS else a + 1
        elif n == 2:  # VC/CV
            cut = a + 2
        else:
            last_two = between[-2].text + between[-1].text
            cut = b - 2 if last_two in BLENDS else a + 3

        cuts.append(cut)
    return cuts


def _split_stem(word: str, offset: int = 0) -> list[Syllable]:
    if not word:
        return []

    # Consonant-le: peel it off and divide what's left.
    if (
        len(word) > 3
        and word.endswith("le")
        and word[-3] not in "aeiouy"
        and any(c in "aeiouy" for c in word[:-3])
    ):
        tail_len = 2 if word[-4:-2] == "ck" else 3
        head, tail = word[:-tail_len], word[-tail_len:]
        tail_start = offset + len(head)
        tail_graphemes = [Grapheme(c, Kind.CONSONANT, tail_start + i) for i, c in enumerate(tail[:-1])]
        tail_graphemes.append(Grapheme("e", Kind.SILENT_E, tail_start + len(tail) - 1))
        return [*_split_stem(head, offset), Syllable(tail, SyllableType.CONSONANT_LE, tuple(tail_graphemes))]

    graphemes = _shift(parse_graphemes(word), offset)
    cuts = _cut_points(word, graphemes)

    syllables: list[Syllable] = []
    start = 0
    for cut in [*cuts, len(graphemes)]:
        chunk = graphemes[start:cut]
        if chunk:
            text = "".join(g.text for g in chunk)
            syllables.append(Syllable(text, _classify(chunk), tuple(chunk)))
        start = cut
    return syllables


def detect_suffix(word: str) -> str | None:
    """Return the suffix we treat as a separate unit, if any."""
    _, ing = split_ing(word)
    if ing:
        return "ing"
    if len(word) > 3 and word.endswith("ed"):
        return "ed"
    if len(word) > 3 and word.endswith("s") and word[-2] not in "aeiousy":
        return "s"
    return None


def _syllabic_ed_stem(word: str) -> str | None:
    """'wanted' -> 'want'. Only -ed after t or d adds a syllable."""
    if len(word) > 4 and word.endswith("ed") and word[-3] in "td":
        stem = word[:-2]
        if any(c in "aeiouy" for c in stem):
            return stem
    return None


def syllabify(word: str) -> list[Syllable]:
    word = word.lower().strip()
    if not word.isalpha():
        return []

    if word in OVERRIDES:
        result: list[Syllable] = []
        pos = 0
        for piece in OVERRIDES[word]:
            graphemes = _shift(parse_graphemes(piece), pos)
            result.append(Syllable(piece, _classify(graphemes), tuple(graphemes)))
            pos += len(piece)
        return result

    stem, suffix = split_ing(word)
    if not suffix:
        ed_stem = _syllabic_ed_stem(word)
        if ed_stem:
            stem, suffix = ed_stem, "ed"

    if not suffix:
        return _split_stem(word)

    # hop-ping, run-ning: a doubled consonant splits across the suffix.
    # Floss doubles (tell-ing, miss-ing) stay with the stem.
    if len(stem) >= 3 and stem[-1] == stem[-2] and stem[-1] not in FLOSS_LETTERS | set("aeiou"):
        head, suffix_text = stem[:-1], stem[-1] + suffix
    else:
        head, suffix_text = stem, suffix

    suffix_graphemes = _shift(parse_graphemes(suffix_text), len(head))
    suffix_syllable = Syllable(suffix_text, _classify(suffix_graphemes), tuple(suffix_graphemes))
    return [*_split_stem(head), suffix_syllable]


def split_syllables(word: str) -> list[str]:
    """Convenience wrapper that just returns the syllable text."""
    return [s.text for s in syllabify(word)] or [word]
