from functools import lru_cache

from app.core.config import get_settings
from app.llm.base import ChatMessage, LLMError, LLMProvider
from app.llm.offline import OfflineProvider
from app.llm.openai_compat import OpenAICompatibleProvider

__all__ = ["ChatMessage", "LLMError", "LLMProvider", "get_fallback_llm", "get_llm"]


@lru_cache
def get_llm() -> LLMProvider:
    settings = get_settings()
    if settings.llm_api_key is None:
        return OfflineProvider()
    return OpenAICompatibleProvider(
        api_key=settings.llm_api_key.get_secret_value(),
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout_seconds,
        default_max_tokens=settings.llm_max_tokens,
    )


@lru_cache
def get_fallback_llm() -> LLMProvider:
    return OfflineProvider()
