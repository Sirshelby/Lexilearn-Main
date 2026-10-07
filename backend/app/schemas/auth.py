import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.learner import AgeBand, LearnerOut, _check_timezone


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)
    account_type: Literal["parent", "teacher", "learner"] = "parent"
    # Every account starts with one learner profile so the app is usable
    # straight away. For a "learner" account it's the person themselves.
    learner_name: str | None = Field(default=None, min_length=1, max_length=40)
    learner_age_band: AgeBand | None = None
    timezone: str = "UTC"

    @field_validator("password")
    @classmethod
    def _not_trivial(cls, value: str) -> str:
        if value.lower() in {"password123", "1234567890", "qwertyuiop"} or len(set(value)) < 4:
            raise ValueError("choose a less common password")
        return value

    @field_validator("timezone")
    @classmethod
    def _tz(cls, value: str) -> str:
        return _check_timezone(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    account_type: str
    learners: list[LearnerOut]


class AuthResponse(TokenResponse):
    user: UserOut
