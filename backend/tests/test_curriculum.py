"""Content checks. If someone edits the curriculum and adds a word that the
learner can't decode yet at that level, these fail in CI."""

import pytest

from app.literacy.curriculum import LEVEL_TITLES, PASSAGES, SKILLS
from app.literacy.decodability import INDEPENDENT_THRESHOLD, analyze_text, analyze_word


def test_skill_codes_are_unique_and_in_order() -> None:
    codes = [s.code for s in SKILLS]
    assert len(codes) == len(set(codes))
    assert [s.level for s in SKILLS] == sorted(s.level for s in SKILLS)
    assert {s.level for s in SKILLS} == set(LEVEL_TITLES)


@pytest.mark.parametrize("skill", SKILLS, ids=lambda s: s.code)
def test_every_practice_word_is_decodable_at_its_level(skill) -> None:
    hard = [w for w in skill.words if not analyze_word(w).decodable_at(skill.level)]
    assert hard == [], f"{skill.code} has words above its level: {hard}"


@pytest.mark.parametrize("skill", SKILLS, ids=lambda s: s.code)
def test_skills_have_enough_words_for_a_session(skill) -> None:
    assert len(skill.words) >= 6


@pytest.mark.parametrize("level", sorted(PASSAGES))
def test_library_passages_are_decodable(level: int) -> None:
    _, text = PASSAGES[level]
    assert analyze_text(text, level).score >= INDEPENDENT_THRESHOLD
