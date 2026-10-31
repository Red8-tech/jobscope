from pathlib import Path
from typing import Any

import pandas as pd

from jobscope.ingestion.cleaning import clean_jobs
from jobscope.models import Job


class CsvSource:
    name = "csv"

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def fetch(self) -> list[Job]:
        raw = pd.read_csv(self._path, dtype=str, keep_default_na=False)
        cleaned = clean_jobs(raw)
        return [self._to_job(row) for row in cleaned.to_dict("records")]

    @staticmethod
    def _to_job(row: dict[str, Any]) -> Job:
        posted = row["posted_at"]
        low, high = row["salary_min"], row["salary_max"]
        return Job(
            source="csv",
            source_id=row["id"],
            title=row["title"],
            company=row["company"],
            url=row["url"],
            category=row["category"],
            location=row["location"],
            salary_text=row["salary"],
            salary_min=None if pd.isna(low) else float(low),
            salary_max=None if pd.isna(high) else float(high),
            salary_currency=row["salary_currency"],
            tags=row["tags"],
            description=row["description"],
            posted_at=None if pd.isna(posted) else pd.Timestamp(posted).to_pydatetime(),
        )