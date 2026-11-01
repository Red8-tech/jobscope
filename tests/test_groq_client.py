import json
from collections.abc import Callable

import httpx
import pytest

from jobscope.ai.llm import GroqClient, LLMError


def make_client(handler: Callable[[httpx.Request], httpx.Response], retries: int = 3) -> GroqClient:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return GroqClient(
        api_key="test-key", model="test-model", client=http, retries=retries, backoff=0
    )


def ok(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_sends_json_mode_request_and_returns_content() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return ok('{"a": 1}')

    assert make_client(handler).complete_json("sys", "usr") == '{"a": 1}'
    body = seen["body"]
    assert isinstance(body, dict)
    assert seen["auth"] == "Bearer test-key"
    assert body["model"] == "test-model"
    assert body["response_format"] == {"type": "json_object"}
    assert body["messages"][0]["role"] == "system"


def test_retries_on_rate_limit_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429) if calls["n"] == 1 else ok("{}")

    assert make_client(handler).complete_json("s", "u") == "{}"
    assert calls["n"] == 2


def test_client_errors_are_not_retried() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(401)

    with pytest.raises(LLMError, match="401"):
        make_client(handler).complete_json("s", "u")
    assert calls["n"] == 1


def test_unexpected_response_shape_raises() -> None:
    client = make_client(lambda request: httpx.Response(200, json={"nope": 1}))
    with pytest.raises(LLMError, match="unexpected"):
        client.complete_json("s", "u")


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(LLMError, match="GROQ_API_KEY"):
        GroqClient()