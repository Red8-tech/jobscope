from datetime import datetime

import pandas as pd
import pytest

from jobscope.ingestion.cleaning import (
    clean_jobs,
    normalize_company,
    normalize_location,
    parse_date,
    parse_salary,
    split_tags,
    strip_html,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Remote", "Worldwide"),
        (" remote ", "Worldwide"),
        ("USA Only", "United States"),
        ("EU", "Europe"),
        ("", "Unspecified"),
        ("India", "India"),
    ],
)
def test_normalize_location(raw: str, expected: str) -> None:
    assert normalize_location(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  ACME ", "Acme"),
        ("acme", "Acme"),
        ("Stark Systems", "Stark Systems"),
        ("  STARK   SYSTEMS", "Stark Systems"),
    ],
)
def test_normalize_company(raw: str, expected: str) -> None:
    assert normalize_company(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-10-28", datetime(2026, 10, 28)),
        ("28/10/2026", datetime(2026, 10, 28)),
        ("Oct 28, 2026", datetime(2026, 10, 28)),
        ("2026-10-28T10:00:00", datetime(2026, 10, 28, 10, 0)),
        ("not a date", None),
        ("", None),
    ],
)
def test_parse_date(raw: str, expected: datetime | None) -> None:
    assert parse_date(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("$90,000", (90000.0, 90000.0, "USD")),
        ("90k-120k", (90000.0, 120000.0, "")),
        ("€70k", (70000.0, 70000.0, "EUR")),
        ("$110,000 - $140,000", (110000.0, 140000.0, "USD")),
        ("$50/hour", None),
        ("competitive", None),
        ("", None),
    ],
)
def test_parse_salary(raw: str, expected: tuple[float, float, str] | None) -> None:
    assert parse_salary(raw) == expected


def test_split_tags_handles_mixed_separators_and_duplicates() -> None:
    assert split_tags("Python;  SQL|python, ") == ["python", "sql"]


def test_strip_html_removes_tags_and_unescapes() -> None:
    assert strip_html("<p>Build <b>APIs</b> &amp; more</p>") == "Build APIs & more"


def test_clean_jobs_dedupes_normalizes_and_drops_untitled(messy_frame: pd.DataFrame) -> None:
    cleaned = clean_jobs(messy_frame)
    assert len(cleaned) == 1
    row = cleaned.iloc[0]
    assert row["company"] == "Acme"
    assert row["location"] == "Worldwide"
    assert row["salary_min"] == 90000.0
    assert row["tags"] == ["python", "sql"]
    assert row["description"] == "Hi"


def test_clean_jobs_rejects_missing_columns() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        clean_jobs(pd.DataFrame({"title": ["x"]}))