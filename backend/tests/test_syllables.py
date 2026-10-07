import pytest

from app.literacy.syllables import SyllableType, split_syllables, syllabify


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        # one syllable, including vowel teams that the old version split up
        ("cat", "cat"),
        ("team", "team"),
        ("rain", "rain"),
        ("boat", "boat"),
        ("light", "light"),
        ("cake", "cake"),
        ("makes", "makes"),
        ("jumped", "jumped"),
        ("fire", "fire"),
        # VC/CV
        ("rabbit", "rab-bit"),
        ("napkin", "nap-kin"),
        ("sunset", "sun-set"),
        ("muffin", "muf-fin"),
        # V/CV and VC/V
        ("robot", "ro-bot"),
        ("tiger", "ti-ger"),
        ("music", "mu-sic"),
        ("cabin", "cab-in"),
        ("rocket", "rock-et"),
        # V/V
        ("lion", "li-on"),
        # VCCCV
        ("hundred", "hun-dred"),
        ("pumpkin", "pump-kin"),
        ("children", "chil-dren"),
        # consonant-le
        ("table", "ta-ble"),
        ("little", "lit-tle"),
        ("candle", "can-dle"),
        ("pickle", "pick-le"),
        # suffixes
        ("jumping", "jump-ing"),
        ("running", "run-ning"),
        ("telling", "tell-ing"),
        ("wanted", "want-ed"),
        ("going", "go-ing"),
        ("playing", "play-ing"),
        # silent e in a longer word
        ("cupcake", "cup-cake"),
        ("inside", "in-side"),
        # r-controlled and y
        ("carrot", "car-rot"),
        ("hero", "he-ro"),
        ("happy", "hap-py"),
        ("baby", "ba-by"),
    ],
)
def test_split(word: str, expected: str) -> None:
    assert "-".join(split_syllables(word)) == expected


def test_syllable_types() -> None:
    types = {s.text: s.type for s in syllabify("cupcake")}
    assert types == {"cup": SyllableType.CLOSED, "cake": SyllableType.VCE}
    assert [s.type for s in syllabify("table")] == [SyllableType.OPEN, SyllableType.CONSONANT_LE]
    assert syllabify("car")[0].type is SyllableType.R_CONTROLLED
    assert syllabify("go")[0].type is SyllableType.OPEN


def test_rejects_non_words() -> None:
    assert syllabify("abc123") == []
    assert split_syllables("") == [""]
