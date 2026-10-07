from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LIBPQ_ONLY_OPTIONS = {"sslmode", "channel_binding", "sslrootcert", "options"}


def normalize_database_url(url: str) -> str:
    """Turn the URL a hosting provider gives you into one SQLAlchemy can use.

    Neon, Supabase and friends hand out URLs like
    postgres://user:pass@host/db?sslmode=require&channel_binding=require.
    SQLAlchemy needs the async driver named in the scheme, and asyncpg
    doesn't understand libpq options like sslmode, so this rewrites them.
    """
    if url.startswith("sqlite"):
        return url
    parts = urlsplit(url)
    scheme = parts.scheme
    if scheme in {"postgres", "postgresql", "postgresql+psycopg", "postgresql+psycopg2"}:
        scheme = "postgresql+asyncpg"

    query = dict(parse_qsl(parts.query))
    sslmode = query.get("sslmode")
    for option in _LIBPQ_ONLY_OPTIONS:
        query.pop(option, None)
    if sslmode and sslmode != "disable" and "ssl" not in query:
        query["ssl"] = sslmode  # asyncpg accepts the same values under this name
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class Settings(BaseSettings):
    """All configuration comes from environment variables (or a .env file).

    Nothing secret has a real default. In development you can run without any
    API keys: the tutor falls back to an offline mode and speech falls back to
    the browser's built-in voices.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    app_name: str = "LexiLearn"
    api_prefix: str = "/api/v1"

    database_url: str = "sqlite+aiosqlite:///./lexilearn.db"
    # Vercel's Neon integration sets DATABASE_URL (pooled) and this one
    # (direct). Migrations use the direct connection when it's available.
    database_url_unpooled: str | None = None
    # True when DATABASE_URL goes through a transaction-mode pooler such as
    # PgBouncer. Left unset, it's detected from Neon's "-pooler" host names.
    database_pooler: bool | None = None
    database_echo: bool = False

    # Vercel sets VERCEL=1 in every build and function. We use it to switch
    # to settings that suit short-lived serverless instances.
    vercel: bool = False

    # Auth
    secret_key: SecretStr = SecretStr("dev-only-secret-change-me-before-deploying")
    access_token_minutes: int = 30
    refresh_token_days: int = 14
    cookie_secure: bool = False  # must be True in production (HTTPS only)

    # Comma separated list of origins allowed to call the API from a browser
    cors_origins: str = "http://localhost:5173"

    # LLM. Anything that speaks the OpenAI chat completions API works here,
    # so this can point at OpenAI, Azure, OpenRouter or a local model server.
    llm_api_key: SecretStr | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 20.0
    llm_max_tokens: int = 350

    # Text to speech (ElevenLabs). Optional.
    elevenlabs_api_key: SecretStr | None = None
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    elevenlabs_model_id: str = "eleven_multilingual_v2"

    # Shared rate limiting across instances. Upstash Redis (from the Vercel
    # Marketplace) provides these; the extra names match what it injects.
    # Without them, limits are kept in memory per process.
    redis_rest_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("REDIS_REST_URL", "UPSTASH_REDIS_REST_URL", "KV_REST_API_URL"),
    )
    redis_rest_token: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("REDIS_REST_TOKEN", "UPSTASH_REDIS_REST_TOKEN", "KV_REST_API_TOKEN"),
    )

    # Rough per-user limits. These protect the paid APIs from runaway clients.
    tutor_messages_per_minute: int = 12
    tts_requests_per_minute: int = 40
    login_attempts_per_minute: int = 8

    log_level: str = "INFO"

    @field_validator("database_url", "database_url_unpooled")
    @classmethod
    def _normalize_db_url(cls, value: str | None) -> str | None:
        return normalize_database_url(value) if value else value

    @property
    def migration_database_url(self) -> str:
        return self.database_url_unpooled or self.database_url

    @property
    def uses_pooler(self) -> bool:
        if self.database_pooler is not None:
            return self.database_pooler
        return "-pooler" in (urlsplit(self.database_url).hostname or "")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
