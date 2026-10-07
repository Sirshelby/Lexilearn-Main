"""Client for any server that implements the OpenAI chat completions API.

I'm calling the HTTP API directly with httpx instead of using the openai SDK.
The original prototype broke when the SDK changed its interface between
versions, and the REST endpoint itself has been stable for years. It also
means the same class works for Azure OpenAI, OpenRouter, Ollama, vLLM etc.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from app.llm.base import ChatMessage, LLMError

log = logging.getLogger(__name__)

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}


class OpenAICompatibleProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        timeout: float = 30.0,
        default_max_tokens: int = 350,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.name = model
        self._model = model
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._default_max_tokens = default_max_tokens
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float = 0.6,
    ) -> str:
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens or self._default_max_tokens,
            "temperature": temperature,
        }

        # One retry at most. Two attempts at the 20 second timeout still fits
        # comfortably inside a 60 second serverless function limit.
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = await self._client.post(self._url, json=payload, headers=self._headers)
            except httpx.HTTPError as exc:
                last_error = exc
            else:
                if response.status_code == 200:
                    return self._extract_text(response.json())
                if response.status_code not in RETRYABLE_STATUS:
                    # 401/403/400 won't get better by retrying
                    log.error("LLM request rejected: %s %s", response.status_code, response.text[:300])
                    raise LLMError(f"provider returned {response.status_code}")
                last_error = LLMError(f"provider returned {response.status_code}")

            if attempt == 0:
                await asyncio.sleep(0.5)

        log.warning("LLM request failed after retries: %s", last_error)
        raise LLMError("provider unavailable") from last_error

    @staticmethod
    def _extract_text(data: dict) -> str:
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("unexpected response shape") from exc
        if not isinstance(text, str) or not text.strip():
            raise LLMError("empty response")
        return text.strip()

    async def aclose(self) -> None:
        await self._client.aclose()
