from datetime import datetime
from pathlib import Path

import pandas as pd

from jobscope.ingestion.csv_source import CsvSource


def test_csv_source_returns_cleaned_jobs(tmp_path: Path, messy_frame: pd.DataFrame) -> None:
    path = tmp_path / "jobs.csv"
    messy_frame.to_csv(path, index=False)

    [job] = CsvSource(path).fetch()

    assert job.source == "csv"
    assert job.company == "Acme"
    assert job.salary_min == 90000.0
    assert job.salary_max == 120000.0
    assert job.posted_at == datetime(2026, 10, 28)
    assert job.tags == ["python", "sql"]