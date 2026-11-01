from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from jobscope.api.schemas import (
    IngestResult,
    JobPage,
    JobSummary,
    MatchList,
    ResumeCreate,
    ResumeCreated,
    SkillTrend,
)
from jobscope.db.repository import JobRepository
from jobscope.ingestion.remotive import IngestionError
from jobscope.models import Job

router = APIRouter()


def get_repo(request: Request) -> Iterator[JobRepository]:
    """One database connection per request, always closed afterwards."""
    repo = JobRepository(request.app.state.db_path)
    try:
        yield repo
    finally:
        repo.close()


Repo = Annotated[JobRepository, Depends(get_repo)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/ingest")
def ingest(request: Request, repo: Repo, source: str = "csv") -> IngestResult:
    factory = request.app.state.sources.get(source)
    if factory is None:
        available = sorted(request.app.state.sources)
        raise HTTPException(status_code=400, detail=f"unknown source; choose from {available}")
    try:
        jobs = factory().fetch()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="source file not found") from exc
    except IngestionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    added = repo.add_jobs(jobs)
    return IngestResult(source=source, fetched=len(jobs), added=added)


@router.get("/jobs")
def list_jobs(repo: Repo, limit: PageSize = 20, offset: Offset = 0) -> JobPage:
    jobs = repo.list_jobs(limit=limit, offset=offset)
    return JobPage(
        items=[JobSummary.model_validate(job) for job in jobs],
        total=repo.count_jobs(),
        limit=limit,
        offset=offset,
    )


@router.get("/jobs/{job_id}")
def get_job(job_id: int, repo: Repo) -> Job:
    job = repo.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.get("/skills/trending")
def trending_skills(repo: Repo, limit: PageSize = 10) -> list[SkillTrend]:
    return [SkillTrend(name=s.name, jobs=s.jobs) for s in repo.top_skills(limit)]


@router.post("/resumes", status_code=201)
def create_resume(payload: ResumeCreate, repo: Repo) -> ResumeCreated:
    return ResumeCreated(id=repo.add_resume(payload.text))


@router.get("/resumes/{resume_id}/matches")
def get_matches(resume_id: int, repo: Repo) -> MatchList:
    if not repo.resume_exists(resume_id):
        raise HTTPException(status_code=404, detail="resume not found")
    # Real matching arrives in Stage 5; the response shape is already final.
    return MatchList(resume_id=resume_id, matches=[])