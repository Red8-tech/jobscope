from typing import NamedTuple

from jobscope.ai.extractor import SkillExtractor
from jobscope.ai.llm import LLMError
from jobscope.db.repository import JobRepository


class BackfillReport(NamedTuple):
    processed: int
    updated: int
    failed: int


def backfill_skills(
    repo: JobRepository, extractor: SkillExtractor, limit: int | None = None
) -> BackfillReport:
    """Extract skills for jobs that have none. One failure never stops the run."""
    jobs = repo.jobs_without_skills()
    if limit is not None:
        jobs = jobs[:limit]
    updated = failed = 0
    for job in jobs:
        if job.id is None:
            continue
        try:
            skills = extractor.extract(f"{job.title}\n{job.description}").skills
        except LLMError:
            failed += 1
            continue
        if skills:
            repo.add_skills(job.id, skills)
            updated += 1
    return BackfillReport(processed=len(jobs), updated=updated, failed=failed)