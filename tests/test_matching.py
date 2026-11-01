import pytest

from jobscope.ai.extractor import SkillExtractor
from jobscope.ai.matching import ResumeMatcher, score_job
from jobscope.models import Job
from tests.fakes import ScriptedClient

RESUME = "Python developer who also uses docker"
LLM_REPLY = '{"skills": ["python", "docker"], "seniority": "mid"}'


def make_job(job_id: int, title: str, tags: list[str], description: str = "") -> Job:
    return Job(id=job_id, source="t", source_id=str(job_id), title=title, company="Acme",
               url="u", tags=tags, description=description)


JOBS = [
    make_job(1, "Python Developer", ["python", "sql"], "build apis"),
    make_job(2, "Frontend Engineer", ["react", "css"]),
    make_job(3, "Backend role", [], "python services"),
]


def make_matcher(**kwargs: object) -> tuple[ResumeMatcher, ScriptedClient]:
    client = ScriptedClient([LLM_REPLY])
    return ResumeMatcher(SkillExtractor(client), **kwargs), client  # type: ignore[arg-type]


def test_score_blends_text_and_skill_overlap() -> None:
    score, matched, gaps = score_job(0.5, {"python"}, {"python", "sql"})
    assert matched == ["python"]
    assert gaps == ["sql"]
    assert score == pytest.approx(0.4 * 0.5 + 0.6 * 0.5)


def test_score_uses_text_alone_when_job_lists_no_skills() -> None:
    assert score_job(0.5, {"python"}, set()) == (0.5, [], [])


def test_matches_rank_by_score_and_report_gaps() -> None:
    matcher, _ = make_matcher()
    results = matcher.match(RESUME, JOBS)
    assert results[0].job_id == 1
    assert results[0].matched == ["python"]
    assert results[0].gaps == ["sql"]
    assert all(result.job_id != 2 for result in results)  # no text overlap, so not retrieved


def test_job_without_skills_has_no_gaps() -> None:
    matcher, _ = make_matcher()
    result = next(r for r in matcher.match(RESUME, JOBS) if r.job_id == 3)
    assert result.gaps == []


def test_limit_caps_results() -> None:
    matcher, _ = make_matcher()
    assert len(matcher.match(RESUME, JOBS, limit=1)) == 1


def test_no_jobs_means_no_model_call() -> None:
    matcher, client = make_matcher()
    assert matcher.match(RESUME, []) == []
    assert client.calls == []


def test_retriever_can_be_swapped() -> None:
    class FixedRetriever:
        def top_k(self, query: str, k: int) -> list[tuple[int, float]]:
            return [(2, 0.9)]

    matcher, _ = make_matcher(retriever_factory=lambda docs: FixedRetriever())
    assert [r.job_id for r in matcher.match(RESUME, JOBS)] == [2]