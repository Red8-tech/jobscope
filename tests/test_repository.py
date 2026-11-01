from collections.abc import Iterator
from datetime import datetime

import pytest

from jobscope.db.repository import (
    CompanyCount,
    JobRepository,
    SkillCount,
)
from jobscope.models import Job, MatchResult


def make_job(
    source_id: str,
    company: str = "Acme",
    tags: tuple[str, ...] = ("python",),
    posted: datetime | None = datetime(2026, 10, 28),
    salary: tuple[float, float, str] | None = None,
) -> Job:
    low, high, currency = salary if salary else (None, None, "")
    return Job(
        source="test",
        source_id=source_id,
        title="Python Developer",
        company=company,
        url=f"https://example.com/{source_id}",
        tags=list(tags),
        posted_at=posted,
        salary_min=low,
        salary_max=high,
        salary_currency=currency,
    )


@pytest.fixture
def repo() -> Iterator[JobRepository]:
    repository = JobRepository()
    yield repository
    repository.close()


def test_add_jobs_is_idempotent(repo: JobRepository) -> None:
    jobs = [make_job("1"), make_job("2")]
    assert repo.add_jobs(jobs) == 2
    assert repo.add_jobs(jobs) == 0
    assert repo.count_jobs() == 2


def test_round_trip_preserves_tags_and_dates(repo: JobRepository) -> None:
    repo.add_jobs([make_job("1", tags=("python", "sql"))])
    [job] = repo.list_jobs()
    assert job.id is not None
    assert set(job.tags) == {"python", "sql"}
    assert job.posted_at == datetime(2026, 10, 28)


def test_top_skills_counts_jobs_per_skill(repo: JobRepository) -> None:
    repo.add_jobs(
        [
            make_job("1", tags=("python", "sql")),
            make_job("2", tags=("python",)),
            make_job("3", tags=("sql", "docker")),
            make_job("4", tags=("python",)),
        ]
    )
    assert repo.top_skills() == [
        SkillCount("python", 3),
        SkillCount("sql", 2),
        SkillCount("docker", 1),
    ]


def test_top_companies_gives_ties_the_same_rank(repo: JobRepository) -> None:
    repo.add_jobs(
        [
            make_job("1", company="Acme"),
            make_job("2", company="Acme"),
            make_job("3", company="Globex"),
            make_job("4", company="Initech"),
        ]
    )
    assert repo.top_companies() == [
        CompanyCount("Acme", 2, 1),
        CompanyCount("Globex", 1, 2),
        CompanyCount("Initech", 1, 2),
    ]


def test_jobs_per_week_groups_by_week(repo: JobRepository) -> None:
    repo.add_jobs(
        [
            make_job("1", posted=datetime(2026, 10, 26)),
            make_job("2", posted=datetime(2026, 10, 28)),
            make_job("3", posted=datetime(2026, 11, 4)),
            make_job("4", posted=None),
        ]
    )
    assert [week.jobs for week in repo.jobs_per_week()] == [2, 1]


def test_salary_by_skill_ignores_thin_data_and_non_usd(repo: JobRepository) -> None:
    repo.add_jobs(
        [
            make_job("1", tags=("python",), salary=(100000, 120000, "USD")),
            make_job("2", tags=("python",), salary=(80000, 100000, "USD")),
            make_job("3", tags=("sql",), salary=(90000, 95000, "USD")),
            make_job("4", tags=("python",), salary=(70000, 80000, "EUR")),
        ]
    )
    [result] = repo.salary_by_skill(min_jobs=2)
    assert result.skill == "python"
    assert result.jobs == 2
    assert result.avg_min == 90000
    assert result.avg_max == 110000


def test_get_job_returns_none_when_missing(repo: JobRepository) -> None:
    repo.add_jobs([make_job("1")])
    [stored] = repo.list_jobs()
    assert stored.id is not None
    assert repo.get_job(stored.id) == stored
    assert repo.get_job(9999) is None


def test_resumes_can_be_stored_and_found(repo: JobRepository) -> None:
    resume_id = repo.add_resume("Python developer, 3 projects")
    assert repo.resume_exists(resume_id)
    assert not repo.resume_exists(resume_id + 1)


def test_matches_are_saved_and_replaced(repo: JobRepository) -> None:

    repo.add_jobs([make_job("1"), make_job("2")])
    first, second = (job.id for job in repo.list_jobs())
    assert first is not None and second is not None
    resume_id = repo.add_resume("Python developer")

    repo.save_matches(
        resume_id,
        [MatchResult(job_id=first, score=0.4, matched=["python"], gaps=["sql"])],
    )
    repo.save_matches(
        resume_id,
        [MatchResult(job_id=second, score=0.9, matched=[], gaps=[])],
    )

    assert [m.job_id for m in repo.get_matches(resume_id)] == [second]


def test_all_jobs_and_resume_text(repo: JobRepository) -> None:
    repo.add_jobs([make_job(str(i)) for i in range(60)])
    assert len(repo.all_jobs()) == 60
    resume_id = repo.add_resume("hello")
    assert repo.get_resume_text(resume_id) == "hello"
    assert repo.get_resume_text(9999) is None