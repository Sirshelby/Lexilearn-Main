"""Prompts for the tutor and the passage writer.

A few rules here come from testing the prototype with the TTS turned on:
emoji and markdown get read out loud ("smiling face with smiling eyes"), and
long answers are hard work for the learners this app is for. So replies are
short, plain text, and split words with hyphens.
"""

from __future__ import annotations

from dataclasses import dataclass

TUTOR_SYSTEM_PROMPT = """You are Lexi, a friendly reading tutor inside LexiLearn,
an app for people with dyslexia. You teach using structured literacy, the approach
behind Orton-Gillingham: explicit, step by step, and multisensory (look, say, trace, write).

How to reply:
- Keep it short: at most 4 sentences unless the learner asks for more.
- Use short, common words and one idea per sentence.
- Plain text only. No emoji, no markdown, no bullet points, no all caps.
  Replies may be read aloud.
- When you split a word, use hyphens, like rab-bit.
- Praise effort in a specific way ("you blended the sounds well"), not generic praise.
- Give one clear thing to try next.
- If the learner makes a mistake, show the correct way kindly and let them try again.

Boundaries:
- You are an AI helper, not a person and not a teacher or specialist. Say so if asked.
- Do not diagnose dyslexia or any condition.
- Never ask for personal details like full name, address, school, phone number or photos.
- Stay on reading, spelling, writing and learning. Gently steer other topics back.
- If the learner seems upset or unsafe, be kind, suggest a short break, and encourage them to talk to
  a trusted adult."""


@dataclass(frozen=True, slots=True)
class LearnerContext:
    name: str
    level: int
    level_title: str
    skill_title: str | None
    skill_focus: str | None
    example_words: tuple[str, ...]
    age_band: str | None
    struggling: bool


def learner_context_prompt(ctx: LearnerContext) -> str:
    lines = [
        f"The learner is called {ctx.name}.",
        f"They are working at level {ctx.level} of 8 ({ctx.level_title}).",
    ]
    if ctx.age_band:
        lines.append(f"Age band: {ctx.age_band}. Match your tone to that age.")
    if ctx.skill_title:
        lines.append(f"Current skill: {ctx.skill_title}. {ctx.skill_focus or ''}".strip())
    if ctx.example_words:
        lines.append("Good practice words for this skill: " + ", ".join(ctx.example_words) + ".")
    lines.append("When you choose your own example words, prefer ones they can already decode at this level.")
    if ctx.struggling:
        lines.append(
            "They have found recent practice hard. Slow down, use easier words and make sure they get a win."
        )
    return "\n".join(lines)


def passage_prompt(level: int, level_title: str, skill_words: list[str], topic: str | None) -> str:
    topic_line = f"The story is about: {topic}." if topic else "Pick a gentle everyday topic."
    return f"""WRITE_PASSAGE LEVEL={level}
Write a short decodable story for a beginning reader at level {level} ({level_title}).
{topic_line}
Rules:
- 4 to 6 short sentences, 35 to 70 words in total.
- Use mostly words like these: {", ".join(skill_words)}.
- Avoid long or irregular words. Use only spelling patterns a reader at this level knows.
- No names of real people or brands. Nothing scary.
- First line: a title of 2 to 4 words. Then the story on the next line. Plain text only."""
