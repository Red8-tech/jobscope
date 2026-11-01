import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from jobscope.ai.llm import LLMClient, LLMError

T = TypeVar("T", bound=BaseModel)


def generate_validated(
    client: LLMClient,
    model: type[T],
    system: str,
    user: str,
    max_attempts: int = 3,
) -> T:
    """Ask the model for JSON, validate it, and retry with the error message if invalid."""
    schema = json.dumps(model.model_json_schema())
    full_system = (
        f"{system}\nRespond with a single JSON object matching this JSON schema:\n{schema}"
    )
    prompt = user
    last_error = ""
    for _ in range(max_attempts):
        raw = client.complete_json(full_system, prompt)
        try:
            return model.model_validate_json(raw)
        except ValidationError as exc:
            last_error = str(exc)
            prompt = (
                f"{user}\n\nYour previous answer was invalid:\n{raw}\n"
                f"Errors:\n{last_error}\nReturn corrected JSON only."
            )
    raise LLMError(f"no valid output after {max_attempts} attempts: {last_error}")