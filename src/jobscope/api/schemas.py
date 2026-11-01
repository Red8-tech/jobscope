from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from jobscope.models import MatchResult


class JobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str
    url: str
    category: str
    location: str
    salary_min: float | None
    salary_max: float | None
    salary_currency: str
    tags: list[str]
    posted_at: datetime | None


class JobPage(BaseModel):
    items: list[JobSummary]
    total: int
    limit: int
    offset: int


class SkillTrend(BaseModel):
    name: str
    jobs: int


class IngestResult(BaseModel):
    source: str
    fetched: int
    added: int


class ResumeCreate(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)


class ResumeCreated(BaseModel):
    id: int


class MatchList(BaseModel):
    resume_id: int
    matches: list[MatchResult]