import sqlite3
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from jobscope.db.schema import SCHEMA
from jobscope.models import Job

# Tags are joined with an ASCII "unit separator" so no real tag can contain it.
_TAG_SEPARATOR = "\x1f"


_INSERT_JOB = """
INSERT OR IGNORE INTO jobs (
    source, source_id, title, company, url, category, job_type, location,
    salary_text, salary_min, salary_max, salary_currency, description, posted_at
) VALUES (
    :source, :source_id, :title, :company, :url, :category, :job_type, :location,
    :salary_text, :salary_min, :salary_max, :salary_currency, :description, :posted_at
)
"""

_SELECT_JOBS = """
SELECT j.*, GROUP_CONCAT(s.name, char(31)) AS tags
FROM jobs j
LEFT JOIN job_skills js ON js.job_id = j.id
LEFT JOIN skills s ON s.id = js.skill_id
GROUP BY j.id
ORDER BY j.posted_at DESC, j.id
LIMIT ? OFFSET ?
"""



class SkillCount(NamedTuple):
    name: str
    jobs: int


class CompanyCount(NamedTuple):
    company: str
    jobs: int
    position: int


class WeeklyCount(NamedTuple):
    week: str
    jobs: int


class SkillSalary(NamedTuple):
    skill: str
    jobs: int
    avg_min: float
    avg_max: float


class JobRepository:
    """All database access lives here; the rest of the app never writes SQL."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def add_jobs(self, jobs: Iterable[Job]) -> int:
        """Insert new jobs and link their skills. Returns how many were new."""
        inserted = 0
        with self._conn:
            for job in jobs:
                cursor = self._conn.execute(_INSERT_JOB, self._job_params(job))
                if cursor.rowcount == 0:
                    continue
                job_id = cursor.lastrowid
                assert job_id is not None
                inserted += 1
                for tag in job.tags:
                    self._conn.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (tag,))
                    self._conn.execute(
                        "INSERT OR IGNORE INTO job_skills (job_id, skill_id) "
                        "SELECT ?, id FROM skills WHERE name = ?",
                        (job_id, tag),
                    )
        return inserted

    def count_jobs(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM jobs").fetchone()
        return int(row[0])

    def list_jobs(self, limit: int = 50, offset: int = 0) -> list[Job]:
        rows = self._conn.execute(_SELECT_JOBS, (limit, offset)).fetchall()
        return [self._row_to_job(row) for row in rows]

    def top_skills(self, limit: int = 10) -> list[SkillCount]:
        rows = self._conn.execute(
            """
            SELECT s.name AS name, COUNT(*) AS jobs
            FROM skills s
            JOIN job_skills js ON js.skill_id = s.id
            GROUP BY s.id
            ORDER BY jobs DESC, name
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [SkillCount(r["name"], r["jobs"]) for r in rows]

    def top_companies(self, limit: int = 10) -> list[CompanyCount]:
        rows = self._conn.execute(
            """
            SELECT company, jobs, RANK() OVER (ORDER BY jobs DESC) AS position
            FROM (SELECT company, COUNT(*) AS jobs FROM jobs GROUP BY company)
            ORDER BY position, company
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [CompanyCount(r["company"], r["jobs"], r["position"]) for r in rows]

    def jobs_per_week(self) -> list[WeeklyCount]:
        rows = self._conn.execute(
            """
            SELECT strftime('%Y-W%W', posted_at) AS week, COUNT(*) AS jobs
            FROM jobs
            WHERE posted_at IS NOT NULL
            GROUP BY week
            ORDER BY week
            """
        ).fetchall()
        return [WeeklyCount(r["week"], r["jobs"]) for r in rows]

    def salary_by_skill(self, min_jobs: int = 3, limit: int = 10) -> list[SkillSalary]:
        """Average yearly USD salary per skill, ignoring skills with too few data points."""
        rows = self._conn.execute(
            """
            SELECT s.name AS skill, COUNT(*) AS jobs,
                   AVG(j.salary_min) AS avg_min, AVG(j.salary_max) AS avg_max
            FROM skills s
            JOIN job_skills js ON js.skill_id = s.id
            JOIN jobs j ON j.id = js.job_id
            WHERE j.salary_min IS NOT NULL AND j.salary_currency = 'USD'
            GROUP BY s.id
            HAVING COUNT(*) >= ?
            ORDER BY avg_max DESC
            LIMIT ?
            """,
            (min_jobs, limit),
        ).fetchall()
        return [SkillSalary(r["skill"], r["jobs"], r["avg_min"], r["avg_max"]) for r in rows]

    @staticmethod
    def _job_params(job: Job) -> dict[str, object]:
        return {
            "source": job.source,
            "source_id": job.source_id,
            "title": job.title,
            "company": job.company,
            "url": job.url,
            "category": job.category,
            "job_type": job.job_type,
            "location": job.location,
            "salary_text": job.salary_text,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "salary_currency": job.salary_currency,
            "description": job.description,
            "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        }

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        posted = row["posted_at"]
        return Job(
            id=row["id"],
            source=row["source"],
            source_id=row["source_id"],
            title=row["title"],
            company=row["company"],
            url=row["url"],
            category=row["category"],
            job_type=row["job_type"],
            location=row["location"],
            salary_text=row["salary_text"],
            salary_min=row["salary_min"],
            salary_max=row["salary_max"],
            salary_currency=row["salary_currency"],
            tags=row["tags"].split(_TAG_SEPARATOR) if row["tags"] else [],
            description=row["description"],
            posted_at=datetime.fromisoformat(posted) if posted else None,
        )