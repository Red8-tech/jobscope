import os
import time
from typing import Any, Protocol

import httpx

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"


class LLMError(Exception):
    """Raised when the language model cannot be reached or misbehaves."""


class LLMClient(Protocol):
    """Anything that can answer a prompt with a JSON string."""

    def complete_json(self, system: str, user: str) -> str:
        ...


class GroqClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        client: httpx.Client | None = None,
        retries: int = 3,
        backoff: float = 1.0,
    ) -> None:
        key = api_key or os.environ.get("GROQ_API_KEY")
        if not key:
            raise LLMError("GROQ_API_KEY is not set")
        self._key = key
        self._model = model or os.environ.get("GROQ_MODEL", DEFAULT_MODEL)
        self._client = client or httpx.Client(timeout=30.0)
        self._retries = retries
        self._backoff = backoff

    def complete_json(self, system: str, user: str) -> str:
        body: dict[str, Any] = {
            "model": self._model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {"Authorization": f"Bearer {self._key}"}
        last_error: Exception | None = None
        for attempt in range(self._retries):
            try:
                response = self._client.post(GROQ_URL, json=body, headers=headers)
                if response.status_code == 429 or response.status_code >= 500:
                    raise LLMError(f"retryable status {response.status_code}")
                response.raise_for_status()
                return str(response.json()["choices"][0]["message"]["content"])
            except (httpx.TransportError, LLMError) as exc:
                last_error = exc
                time.sleep(self._backoff * 2**attempt)
            except httpx.HTTPStatusError as exc:
                raise LLMError(f"request rejected with status {exc.response.status_code}") from exc
            except (KeyError, IndexError, ValueError) as exc:
                raise LLMError("unexpected response shape from model API") from exc
        raise LLMError(f"failed after {self._retries} attempts") from last_error