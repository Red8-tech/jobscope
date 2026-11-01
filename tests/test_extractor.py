from jobscope.ai.extractor import MAX_CHARS, SkillExtractor
from tests.fakes import ScriptedClient


def test_normalizes_and_dedupes_skills() -> None:
    client = ScriptedClient(['{"skills": ["Python", "  SQL ", "python", ""], "seniority": "mid"}'])
    result = SkillExtractor(client).extract("We use Python and SQL")
    assert result.skills == ["python", "sql"]
    assert result.seniority == "mid"


def test_invalid_seniority_triggers_retry() -> None:
    client = ScriptedClient(
        ['{"skills": ["go"], "seniority": "wizard"}', '{"skills": ["go"], "seniority": "senior"}']
    )
    result = SkillExtractor(client).extract("Go developer")
    assert result.seniority == "senior"
    assert len(client.calls) == 2


def test_empty_text_makes_no_model_call() -> None:
    client = ScriptedClient([])
    assert SkillExtractor(client).extract("   ").skills == []
    assert client.calls == []


def test_long_text_is_truncated() -> None:
    client = ScriptedClient(['{"skills": []}'])
    SkillExtractor(client).extract("x" * (MAX_CHARS * 2))
    assert len(client.calls[0][1]) == MAX_CHARS