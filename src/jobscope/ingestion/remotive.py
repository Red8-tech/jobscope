import time
from typing import Any

import httpx

from jobscope.models import Job

API_URL = "https://remotive.com/api/remote-jobs"



class IngestionError(Exception):
    """Raised when a job source cannot be read."""


class RemotiveSource:
    name = "remotive"

    def __init__(
        self,
        client: httpx.Client | None = None,
        retries: int = 3,
        backoff: float = 1.0,
    ) -> None:
        self._client = client or httpx.Client(timeout=10.0)
        self._retries = retries
        self._backoff = backoff

    def fetch(self) -> list[Job]:
        payload = self._get_json()
        return [self._to_job(raw) for raw in payload.get("jobs", [])]

    def _get_json(self) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self._retries):
            try:
                response = self._client.get(API_URL)
                if response.status_code == 429 or response.status_code >= 500:
                    raise IngestionError(f"retryable status {response.status_code}")
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                return data
            except (httpx.TransportError, IngestionError) as exc:
                last_error = exc
                time.sleep(self._backoff * 2**attempt)
        raise IngestionError(f"failed after {self._retries} attempts") from last_error

    @staticmethod
    def _to_job(raw: dict[str, Any]) -> Job:
        return Job(
            source="remotive",
            source_id=str(raw["id"]),
            title=raw["title"],
            company=raw["company_name"],
            url=raw["url"],
            category=raw.get("category") or "",
            job_type=raw.get("job_type") or "",
            location=raw.get("candidate_required_location") or "",
            salary_text=raw.get("salary") or "",
            tags=raw.get("tags") or [],
            description=raw.get("description") or "",
            posted_at=raw.get("publication_date"),
        )