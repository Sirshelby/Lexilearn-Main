"""
Works out which phonics patterns a word uses and therefore which level a
learner needs to be at to sound it out.

A word is "decodable" at a level if every pattern in it has been taught by
that level, or if it's a heart word that has already been introduced.
A passage's decodability is just the percentage of its words that are.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from app.literacy.curriculum import (
    PATTERN_LABELS,
    PATTERN_LEVELS,
    Pattern,
    heart_word_level,
)
from app.literacy.graphemes import DIPHTHONGS, Kind, parse_graphemes
from app.literacy.syllables import Syllable, SyllableType, syllabify

# Reading accuracy bands commonly used for levelling texts: 95%+ is
# comfortable to read alone, 90-94% is fine with an adult nearby, and below
# 90% tends to frustrate the reader.
INDEPENDENT_THRESHOLD = 95.0
INSTRUCTIONAL_THRESHOLD = 90.0

_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

_SYLLABLE_PATTERNS = {
    SyllableType.CLOSED: Pattern.CLOSED,
    SyllableType.OPEN: Pattern.OPEN,
    SyllableType.VCE: Pattern.VCE,
    SyllableType.VOWEL_TEAM: Pattern.VOWEL_TEAM,
    SyllableType.R_CONTROLLED: Pattern.R_CONTROLLED,
    SyllableType.CONSONANT_LE: Pattern.CONSONANT_LE,
}


@dataclass(frozen=True, slots=True)
class WordAnalysis:
    word: str
    syllables: tuple[Syllable, ...]
    patterns: frozenset[Pattern]
    required_level: int | None  # None: the rules can't sound this word out
    heart_word_level: int | None

    def decodable_at(self, level: int) -> bool:
        if self.heart_word_level is not None and self.heart_word_level <= level:
            return True
        return self.required_level is not None and self.required_level <= level

    @property
    def sound_count(self) -> int | None:
        """Number of sounds (phonemes), used by the 'count the sounds' exercise."""
        if self.required_level is None:
            return None
        count = 0
        previous = ""
        for syllable in self.syllables:
            for g in syllable.graphemes:
                if g.kind is Kind.SILENT_E:
                    continue
                if g.kind is Kind.CONSONANT and g.text == previous:
                    continue  # bell, rabbit: a double letter is one sound
                count += 2 if g.text in {"x", "qu", "nk"} else 1
                previous = g.text
        return count

    def describe_patterns(self) -> list[str]:
        ordered = sorted(self.patterns, key=lambda p: (PATTERN_LEVELS[p], p.value))
        return [PATTERN_LABELS[p] for p in ordered]


def _consonant_runs(syllable: Syllable) -> list[list[str]]:
    runs: list[list[str]] = []
    current: list[str] = []
    for g in syllable.graphemes:
        if g.is_consonant:
            current.append(g.text)
        else:
            if current:
                runs.append(current)
            current = []
    if current:
        runs.append(current)
    return runs


def _has_suffix_ed(word: str) -> bool:
    graphemes = parse_graphemes(word)
    if len(graphemes) < 3 or graphemes[-1].text != "d" or graphemes[-2].text != "e":
        return False
    return any(g.is_nucleus for g in graphemes[:-2]) and word not in {"hundred", "sacred", "naked", "wicked"}


@lru_cache(maxsize=20_000)
def analyze_word(raw: str) -> WordAnalysis:
    word = raw.lower().strip()
    heart = heart_word_level(word.replace("'", ""))

    contraction = "'" in word
    base = word.split("'")[0] if contraction else word
    syllables = tuple(syllabify(base))

    if not syllables:
        return WordAnalysis(word, (), frozenset(), None, heart)

    patterns: set[Pattern] = set()
    irregular = False

    if contraction:
        patterns.add(Pattern.CONTRACTION)
    if len(syllables) > 1:
        patterns.add(Pattern.MULTISYLLABLE)

    ends_with_suffix_s = len(base) > 3 and base.endswith("s") and base[-2] not in "aeiousy"
    if ends_with_suffix_s:
        patterns.add(Pattern.SUFFIX_S)

    if base.endswith("ing") and len(syllables) > 1 and syllables[-1].text.endswith("ing"):
        patterns.add(Pattern.SUFFIX_ING)
    elif _has_suffix_ed(base):
        patterns.add(Pattern.SUFFIX_ED)

    for index, syllable in enumerate(syllables):
        if syllable.type is SyllableType.IRREGULAR:
            irregular = True
            continue

        pattern = _SYLLABLE_PATTERNS[syllable.type]
        if syllable.type is SyllableType.VOWEL_TEAM:
            teams = [g.text for g in syllable.graphemes if g.kind is Kind.VOWEL_TEAM]
            if teams and all(t in DIPHTHONGS for t in teams):
                pattern = Pattern.DIPHTHONG
        patterns.add(pattern)
        is_last = index == len(syllables) - 1

        for g in syllable.graphemes:
            if g.kind is Kind.DIGRAPH:
                patterns.add(Pattern.DIGRAPH)
            elif g.kind is Kind.WELDED:
                patterns.add(Pattern.WELDED)
            elif g.kind is Kind.TRIGRAPH:
                patterns.add(Pattern.TRIGRAPH)
            elif g.kind is Kind.ADVANCED:
                patterns.add(Pattern.ADVANCED_SPELLING)
            elif g.kind is Kind.IRREGULAR:
                irregular = True
            elif g.kind is Kind.VOWEL and g.text == "y":
                patterns.add(Pattern.Y_AS_VOWEL)
            elif g.kind is Kind.CONSONANT and g.text == "c":
                nxt = base[g.start + 1] if g.start + 1 < len(base) else ""
                if nxt in {"e", "i", "y"}:
                    patterns.add(Pattern.SOFT_C_G)
            elif (
                g.kind is Kind.CONSONANT
                and g.text == "g"
                and base.endswith("ge")
                and g.start == len(base) - 2
            ):
                patterns.add(Pattern.SOFT_C_G)
            elif (
                g.kind is Kind.SILENT_E
                and syllable.type not in {SyllableType.VCE, SyllableType.CONSONANT_LE}
                and Pattern.SUFFIX_ED not in patterns
            ):
                patterns.add(Pattern.SILENT_E_OTHER)

        if syllable.type is SyllableType.CONSONANT_LE:
            continue
        for run in _consonant_runs(syllable):
            if is_last and ends_with_suffix_s and run[-1] == "s":
                run = run[:-1]
            if len(run) < 2:
                continue
            if len(run) == 2 and run[0] == run[1]:
                patterns.add(Pattern.FLOSS)
            else:
                patterns.add(Pattern.BLEND)

    required = None if irregular else max(PATTERN_LEVELS[p] for p in patterns)
    return WordAnalysis(word, syllables, frozenset(patterns), required, heart)


@dataclass(frozen=True, slots=True)
class WordResult:
    word: str
    decodable: bool
    required_level: int | None
    is_heart_word: bool


@dataclass(frozen=True, slots=True)
class TextReport:
    level: int
    total_words: int
    decodable_words: int
    score: float
    band: str
    words: tuple[WordResult, ...]
    tricky_words: tuple[str, ...]


def tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text)


def band_for(score: float) -> str:
    if score >= INDEPENDENT_THRESHOLD:
        return "independent"
    if score >= INSTRUCTIONAL_THRESHOLD:
        return "with_support"
    return "too_hard"


def analyze_text(text: str, level: int) -> TextReport:
    results: list[WordResult] = []
    tricky: dict[str, None] = {}  # dict keeps first-seen order

    for token in tokenize(text):
        analysis = analyze_word(token)
        ok = analysis.decodable_at(level)
        is_heart = analysis.heart_word_level is not None and analysis.heart_word_level <= level
        results.append(WordResult(token, ok, analysis.required_level, is_heart))
        if not ok:
            tricky[token.lower()] = None

    total = len(results)
    decodable = sum(r.decodable for r in results)
    score = round(100.0 * decodable / total, 1) if total else 100.0
    return TextReport(level, total, decodable, score, band_for(score), tuple(results), tuple(tricky))
