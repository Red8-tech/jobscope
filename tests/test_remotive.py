from collections.abc import Callable

import httpx
import pytest

from jobscope.ingestion.remotive import IngestionError, RemotiveSource

RAW_JOB = {
    "id": 101,
    "url": "https://remotive.com/job/101",
    "title": "Python Developer",
    "company_name": "Acme",
    "category": "Software Development",
    "tags": ["python", "sql"],
    "job_type": "full_time",
    "publication_date": "2026-10-28T10:00:00",
    "candidate_required_location": "Worldwide",
    "salary": "",
    "description": "<p>Build APIs</p>",
}



def make_source(
    handler: Callable[[httpx.Request], httpx.Response], retries: int = 3
) -> RemotiveSource:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return RemotiveSource(client=client, retries=retries, backoff=0)


def test_fetch_maps_fields_to_job() -> None:
    source = make_source(lambda request: httpx.Response(200, json={"jobs": [RAW_JOB]}))
    [job] = source.fetch()
    assert job.source_id == "101"
    assert job.company == "Acme"
    assert job.location == "Worldwide"
    assert job.tags == ["python", "sql"]
    assert job.posted_at is not None


def test_missing_optional_fields_become_empty() -> None:
    minimal = {"id": 1, "url": "u", "title": "t", "company_name": "c"}
    source = make_source(lambda request: httpx.Response(200, json={"jobs": [minimal]}))
    [job] = source.fetch()
    assert job.salary_text == ""
    assert job.tags == []
    assert job.posted_at is None


def test_retries_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"jobs": [RAW_JOB]})

    assert len(make_source(handler).fetch()) == 1
    assert calls["n"] == 2


def test_gives_up_after_retries() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503)

    with pytest.raises(IngestionError):
        make_source(handler, retries=3).fetch()
    assert calls["n"] == 3