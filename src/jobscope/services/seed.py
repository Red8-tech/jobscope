import json
from pathlib import Path

from jobscope.db.repository import JobRepository
from jobscope.ingestion.sources import JobSource


def seed_if_empty(
    repo: JobRepository, source: JobSource, skills_snapshot: Path | None = None
) -> int:
    """Load jobs on a fresh database, then restore saved skills. Never calls a model."""
    if repo.count_jobs() > 0:
        return 0
    added = repo.add_jobs(source.fetch())
    if skills_snapshot is not None and skills_snapshot.exists():
        snapshot: dict[str, list[str]] = json.loads(skills_snapshot.read_text(encoding="utf-8"))
        for job in repo.jobs_without_skills():
            skills = snapshot.get(job.source_id)
            if skills and job.id is not None:
                repo.add_skills(job.id, skills)
    return added