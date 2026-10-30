from typing import Protocol

from jobscope.models import Job


class JobSource(Protocol):
    """Anything that can produce jobs: an API, a CSV file, a scraper."""

    name: str
    def fetch(self) -> list[Job]:
        ...