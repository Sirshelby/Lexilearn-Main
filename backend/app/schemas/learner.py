import uuid
from datetime import datetime
from functools import lru_cache
from typing import Literal
from zoneinfo import available_timezones

from pydantic import BaseModel, ConfigDict, Field, field_validator

AgeBand = Literal["5-7", "8-10", "11-13", "14-17", "18+"]


class ReadingPreferences(BaseModel):
    """Per-learner reading settings. Defaults follow the British Dyslexia
    Association style guide: a clear sans-serif, larger text, extra spacing
    and a soft background instead of bright white."""

    font: Literal["lexend", "atkinson", "opendyslexic", "system"] = "lexend"
    text_size: int = Field(default=20, ge=16, le=32)
    letter_spacing: Literal["normal", "wide", "wider"] = "wide"
    line_spacing: Literal["normal", "relaxed", "loose"] = "relaxed"
    theme: Literal["soft", "cream", "dark", "high_contrast"] = "soft"
    overlay: Literal["none", "blue", "yellow", "green", "rose", "peach"] = "none"
    speech_rate: float = Field(default=0.9, ge=0.5, le=1.5)
    premium_voice: bool = True
    show_syllable_colours: bool = True


@lru_cache(maxsize=1)
def _timezones() -> frozenset[str]:
    return frozenset(available_timezones())


def _check_timezone(value: str) -> str:
    if value not in _timezones():
        raise ValueError("unknown timezone")
    return value


class LearnerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    age_band: AgeBand | None = None
    timezone: str = "UTC"

    @field_validator("timezone")
    @classmethod
    def _tz(cls, value: str) -> str:
        return _check_timezone(value)


class LearnerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    age_band: AgeBand | None = None
    timezone: str | None = None
    preferences: ReadingPreferences | None = None

    @field_validator("timezone")
    @classmethod
    def _tz(cls, value: str | None) -> str | None:
        return None if value is None else _check_timezone(value)


class LearnerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    age_band: str | None
    timezone: str
    preferences: ReadingPreferences
    created_at: datetime

    @field_validator("preferences", mode="before")
    @classmethod
    def _fill_defaults(cls, value: object) -> object:
        # Older rows may be missing newer keys; let the model fill them in.
        return value or {}
