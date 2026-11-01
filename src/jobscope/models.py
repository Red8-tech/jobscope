from datetime import datetime

from pydantic import BaseModel, Field


class Job(BaseModel):
    """A single job listing in our normalized, source-independent form."""

    id: int | None = None
    source: str
    source_id: str
    title: str
    company: str
    url: str
    category: str = ""
    job_type: str = ""
    location: str = ""
    salary_text: str = ""
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str = ""
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    posted_at: datetime | None = None


class MatchResult(BaseModel):
    """How well one job fits a resume."""

    job_id: int
    score: float
    matched: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)