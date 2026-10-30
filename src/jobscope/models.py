from datetime import datetime

from pydantic import BaseModel, Field


class Job(BaseModel):
    """A single job listing in our normalized, source-independent form."""

    source: str
    source_id: str
    title: str
    company: str
    url: str
    category: str = ""
    job_type: str = ""
    location: str = ""
    salary_text: str = ""
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    posted_at: datetime | None = None