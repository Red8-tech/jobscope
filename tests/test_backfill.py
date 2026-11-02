from collections.abc import Iterator

import pytest

from jobscope.ai.extractor import SkillExtractor
from jobscope.db.repository import JobRepository
from jobscope.models import Job
from jobscope.services.backfill import BackfillReport, backfill_skills
from tests.fakes import ScriptedClient


def make_job(source_id: str, tags: list[str], description: str = "") -> Job:
    return Job(source="t", source_id=source_id, title="Dev", company="Acme",
               url="u", tags=tags, description=description)


@pytest.fixture
def repo() -> Iterator[JobRepository]:
    repository = JobRepository()
    yield repository
    repository.close()


def test_fills_only_jobs_without_skills(repo: JobRepository) -> None:
    repo.add_jobs([make_job("1", ["python"]), make_job("2", [], "needs redis and git")])
    client = ScriptedClient(['{"skills": ["redis", "git"], "seniority": "unknown"}'])

    report = backfill_skills(repo, SkillExtractor(client))

    assert report == BackfillReport(processed=1, updated=1, failed=0)
    assert len(client.calls) == 1
    assert repo.jobs_without_skills() == []


def test_one_failure_does_not_stop_the_run(repo: JobRepository) -> None:
    repo.add_jobs([make_job("1", [], "a"), make_job("2", [], "b")])
    # Job 1 gets three invalid replies (the extractor's retry limit); job 2 then succeeds.
    client = ScriptedClient(["bad", "bad", "bad", '{"skills": ["go"]}'])

    report = backfill_skills(repo, SkillExtractor(client))

    assert report == BackfillReport(processed=2, updated=1, failed=1)
    assert len(repo.jobs_without_skills()) == 1


def test_limit_caps_how_many_jobs_are_processed(repo: JobRepository) -> None:
    repo.add_jobs([make_job(str(i), [], "text") for i in range(3)])
    client = ScriptedClient(['{"skills": ["go"]}'] * 2)

    report = backfill_skills(repo, SkillExtractor(client), limit=2)

    assert report.processed == 2
    assert len(repo.jobs_without_skills()) == 1


def test_job_stays_untagged_when_no_skills_are_found(repo: JobRepository) -> None:
    repo.add_jobs([make_job("1", [], "teamwork and communication")])
    client = ScriptedClient(['{"skills": []}'])

    report = backfill_skills(repo, SkillExtractor(client))

    assert report == BackfillReport(processed=1, updated=0, failed=0)
    assert len(repo.jobs_without_skills()) == 1