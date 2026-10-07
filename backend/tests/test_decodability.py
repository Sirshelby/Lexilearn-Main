import pytest

from app.literacy.curriculum import Pattern
from app.literacy.decodability import analyze_text, analyze_word, band_for


@pytest.mark.parametrize(
    ("word", "level"),
    [
        ("cat", 1),
        ("cats", 1),
        ("ship", 2),
        ("bell", 2),
        ("ring", 2),
        ("stop", 3),
        ("match", 3),
        ("cake", 4),
        ("go", 4),
        ("rabbit", 5),
        ("jumping", 5),
        ("happy", 5),
        ("rain", 6),
        ("car", 7),
        ("table", 8),
        ("coin", 8),
        ("city", 8),
    ],
)
def test_required_level(word: str, level: int) -> None:
    assert analyze_word(word).required_level == level


def test_irregular_words_need_to_be_heart_words() -> None:
    through = analyze_word("through")
    assert through.required_level is None
    assert not through.decodable_at(4)
    assert through.decodable_at(5)  # introduced as a heart word at level 5


def test_classic_decodable_sentence() -> None:
    # The old prototype scored this 50% and called it "far too difficult".
    report = analyze_text("The cat sat on the mat.", level=1)
    assert report.score == 100.0
    assert report.band == "independent"


def test_tricky_words_are_reported_once() -> None:
    report = analyze_text("The ship and the ship sail.", level=1)
    assert report.tricky_words == ("ship", "sail")
    assert report.total_words == 6


def test_vowel_team_vs_diphthong() -> None:
    assert Pattern.VOWEL_TEAM in analyze_word("boat").patterns
    assert Pattern.DIPHTHONG in analyze_word("coin").patterns
    assert Pattern.VOWEL_TEAM not in analyze_word("coin").patterns


@pytest.mark.parametrize(
    ("word", "count"),
    [("cat", 3), ("ship", 3), ("bell", 3), ("cake", 3), ("jump", 4), ("box", 4), ("rabbit", 5)],
)
def test_sound_count(word: str, count: int) -> None:
    assert analyze_word(word).sound_count == count


def test_bands() -> None:
    assert band_for(96) == "independent"
    assert band_for(92) == "with_support"
    assert band_for(70) == "too_hard"
