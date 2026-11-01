import pytest
from pydantic import BaseModel

from jobscope.ai.llm import LLMError
from jobscope.ai.structured import generate_validated
from tests.fakes import ScriptedClient


class Answer(BaseModel):
    value: int


def test_returns_validated_model_on_first_try() -> None:
    client = ScriptedClient(['{"value": 7}'])
    assert generate_validated(client, Answer, "sys", "usr") == Answer(value=7)
    assert len(client.calls) == 1
    assert "JSON" in client.calls[0][0]


def test_retries_with_error_feedback_after_invalid_output() -> None:
    client = ScriptedClient(["not json at all", '{"value": 3}'])
    assert generate_validated(client, Answer, "sys", "usr").value == 3
    assert len(client.calls) == 2
    assert "invalid" in client.calls[1][1]


def test_gives_up_after_max_attempts() -> None:
    client = ScriptedClient(['{"value": "x"}'] * 3)
    with pytest.raises(LLMError, match="3 attempts"):
        generate_validated(client, Answer, "sys", "usr")
    assert len(client.calls) == 3