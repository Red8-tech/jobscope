import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from jobscope.db.repository import JobRepository
from jobscope.models import Job
from jobscope.services.seed import seed_if_empty


class StubSource:
    name = "stub"

    def fetch(self) -> list[Job]:
        return [
            Job(source="csv", source_id="1", title="Dev", company="A", url="u", tags=["python"]),
            Job(source="csv", source_id="2", title="Dev", company="B", url="u"),
        ]


@pytest.fixture
def repo() -> Iterator[JobRepository]:
    repository = JobRepository()
    yield repository
    repository.close()


def test_seeds_empty_database_and_restores_snapshot(repo: JobRepository, tmp_path: Path) -> None:
    snapshot = tmp_path / "skills.json"
    snapshot.write_text(json.dumps({"2": ["redis"]}), encoding="utf-8")

    assert seed_if_empty(repo, StubSource(), snapshot) == 2
    assert repo.jobs_without_skills() == []


def test_does_nothing_when_database_already_has_jobs(repo: JobRepository) -> None:
    seed_if_empty(repo, StubSource())
    assert seed_if_empty(repo, StubSource()) == 0
    assert repo.count_jobs() == 2


def test_missing_snapshot_file_is_not_an_error(repo: JobRepository, tmp_path: Path) -> None:
    seed_if_empty(repo, StubSource(), tmp_path / "missing.json")
    assert len(repo.jobs_without_skills()) == 1