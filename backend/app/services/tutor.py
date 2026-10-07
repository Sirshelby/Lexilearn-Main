"""Chat with Lexi: builds the prompt, calls the model, stores the messages."""

from __future__ import annotations

import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.literacy.curriculum import LEVEL_TITLES, MAX_LEVEL
from app.llm import ChatMessage, LLMError, LLMProvider
from app.llm.prompts import TUTOR_SYSTEM_PROMPT, LearnerContext, learner_context_prompt
from app.models import Conversation, Learner, Message
from app.services.progress import current_skill, is_struggling, load_progress

log = logging.getLogger(__name__)

HISTORY_LIMIT = 12  # messages of context sent to the model
MAX_REPLY_CHARS = 1200

_EMOJI = re.compile("[\U0001f000-\U0001faff\u2600-\u27bf\ufe0f\u200d]")
_MARKDOWN = re.compile(r"(\*\*|__|`|^#+\s*|^\s*[-*]\s+)", re.M)


def clean_reply(text: str) -> str:
    """Belt and braces: the prompt asks for plain text, but models slip."""
    text = _EMOJI.sub("", text)
    text = _MARKDOWN.sub("", text)
    text = re.sub(r"[ \t]{2,}", " ", text).strip()
    if len(text) > MAX_REPLY_CHARS:
        cut = text[:MAX_REPLY_CHARS].rsplit(". ", 1)[0]
        text = cut + "."
    return text


async def build_context(db: AsyncSession, learner: Learner) -> LearnerContext:
    progress = await load_progress(db, learner.id)
    skill = current_skill(progress)
    level = skill.level if skill else MAX_LEVEL
    return LearnerContext(
        name=learner.name,
        level=level,
        level_title=LEVEL_TITLES[level],
        skill_title=skill.title if skill else None,
        skill_focus=skill.focus if skill else None,
        example_words=skill.words[:6] if skill else (),
        age_band=learner.age_band,
        struggling=is_struggling(progress.get(skill.code)) if skill else False,
    )


def _title_from(text: str) -> str:
    words = re.findall(r"[A-Za-z']+", text)[:6]
    return (" ".join(words) or "New chat")[:120]


async def send_message(
    db: AsyncSession,
    learner: Learner,
    conversation: Conversation,
    content: str,
    llm: LLMProvider,
    fallback: LLMProvider,
) -> tuple[Message, Message]:
    user_message = Message(conversation_id=conversation.id, role="user", content=content.strip())
    db.add(user_message)
    await db.flush()

    history = list(
        await db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(HISTORY_LIMIT)
        )
    )
    history.reverse()

    context = await build_context(db, learner)
    prompt = [
        ChatMessage("system", TUTOR_SYSTEM_PROMPT),
        ChatMessage("system", learner_context_prompt(context)),
        *(ChatMessage(m.role, m.content) for m in history),  # type: ignore[arg-type]
    ]

    try:
        text = await llm.complete(prompt)
        model = llm.name
    except LLMError:
        log.warning("tutor falling back to offline provider")
        text = await fallback.complete(prompt)
        model = f"{fallback.name}-fallback"

    reply = Message(conversation_id=conversation.id, role="assistant", content=clean_reply(text), model=model)
    db.add(reply)

    if conversation.title == "New chat":
        conversation.title = _title_from(content)
    conversation.updated_at = utcnow()

    await db.commit()
    return user_message, reply
