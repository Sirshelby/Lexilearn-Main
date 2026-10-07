"""Text to speech through ElevenLabs, cached in the database.

Most requests are for the same short practice words ("cat", "ship"), so
after the first time they cost nothing. Only short texts are cached, so
the table doesn't fill up with one-off passages.

If no key is configured this raises SpeechUnavailable and the frontend uses
the browser's built-in speechSynthesis instead.
"""

from __future__ import annotations

import hashlib
import logging

import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import TTSClip

log = logging.getLogger(__name__)

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
CACHE_MAX_CHARS = 120


class SpeechUnavailable(Exception):
    pass


def cache_key(text: str, slow: bool) -> str:
    s = get_settings()
    raw = f"{s.elevenlabs_voice_id}|{s.elevenlabs_model_id}|{slow}|{text}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def synthesize(
    db: AsyncSession, text: str, slow: bool = False, client: httpx.AsyncClient | None = None
) -> bytes:
    settings = get_settings()
    if settings.elevenlabs_api_key is None:
        raise SpeechUnavailable("no speech provider configured")

    key = cache_key(text, slow)
    cached = await db.get(TTSClip, key)
    if cached is not None:
        return cached.audio

    body = {
        "text": text,
        "model_id": settings.elevenlabs_model_id,
        "voice_settings": {"stability": 0.6, "similarity_boost": 0.75, "speed": 0.8 if slow else 1.0},
    }
    headers = {"xi-api-key": settings.elevenlabs_api_key.get_secret_value(), "accept": "audio/mpeg"}
    url = ELEVENLABS_URL.format(voice_id=settings.elevenlabs_voice_id)

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=20)
    try:
        response = await client.post(
            url, json=body, headers=headers, params={"output_format": "mp3_44100_64"}
        )
    except httpx.HTTPError as exc:
        raise SpeechUnavailable("speech provider unreachable") from exc
    finally:
        if owns_client:
            await client.aclose()

    if response.status_code != 200:
        log.warning("ElevenLabs returned %s", response.status_code)
        raise SpeechUnavailable(f"speech provider returned {response.status_code}")

    audio = response.content
    if len(text) <= CACHE_MAX_CHARS:
        db.add(TTSClip(key=key, audio=audio))
        try:
            await db.commit()
        except IntegrityError:
            # Another request cached the same clip a moment ago. That's fine.
            await db.rollback()
    return audio
