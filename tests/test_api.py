from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from jobscope.api.app import create_app
from jobscope.ingestion.remotive import IngestionError
from jobscope.models import Job


class FakeSource:
    name = "fake"

    def fetch(self) -> list[Job]:
        return [
            Job(source="fake", source_id="1", title="Python Dev", company="Acme",
                url="u1", tags=["python", "sql"], description="Build APIs",
                posted_at=datetime(2026, 10, 28)),
            Job(source="fake", source_id="2", title="Data Analyst", company="Globex",
                url="u2", tags=["python"], posted_at=datetime(2026, 10, 27)),
            Job(source="fake", source_id="3", title="DevOps", company="Acme",
                url="u3", tags=["docker"], posted_at=datetime(2026, 10, 26)),
        ]


class FailingSource:
    name = "failing"

    def fetch(self) -> list[Job]:
        raise IngestionError("upstream down")


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    sources = {"fake": FakeSource, "failing": FailingSource}
    app = create_app(db_path=tmp_path / "test.db", sources=sources)
    with TestClient(app) as test_client:
        yield test_client


def ingest_fake(client: TestClient) -> None:
    assert client.post("/ingest", params={"source": "fake"}).status_code == 200


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_ingest_is_idempotent(client: TestClient) -> None:
    first = client.post("/ingest", params={"source": "fake"}).json()
    second = client.post("/ingest", params={"source": "fake"}).json()
    assert first == {"source": "fake", "fetched": 3, "added": 3}
    assert second == {"source": "fake", "fetched": 3, "added": 0}


def test_ingest_unknown_source_is_400(client: TestClient) -> None:
    response = client.post("/ingest", params={"source": "nope"})
    assert response.status_code == 400
    assert "fake" in response.json()["detail"]


def test_ingest_upstream_failure_is_502(client: TestClient) -> None:
    response = client.post("/ingest", params={"source": "failing"})
    assert response.status_code == 502
    assert "upstream down" in response.json()["detail"]


def test_jobs_are_paginated_and_summarised(client: TestClient) -> None:
    ingest_fake(client)
    page = client.get("/jobs", params={"limit": 2}).json()
    assert page["total"] == 3
    assert len(page["items"]) == 2
    assert "description" not in page["items"][0]


def test_jobs_rejects_invalid_page_size(client: TestClient) -> None:
    assert client.get("/jobs", params={"limit": 0}).status_code == 422
    assert client.get("/jobs", params={"limit": 101}).status_code == 422


def test_job_detail_and_404(client: TestClient) -> None:
    ingest_fake(client)
    job_id = client.get("/jobs").json()["items"][0]["id"]
    detail = client.get(f"/jobs/{job_id}")
    assert detail.status_code == 200
    assert detail.json()["description"]
    assert client.get("/jobs/9999").status_code == 404


def test_trending_skills(client: TestClient) -> None:
    ingest_fake(client)
    skills = client.get("/skills/trending").json()
    assert skills[0] == {"name": "python", "jobs": 2}


def test_resume_flow(client: TestClient) -> None:
    created = client.post("/resumes", json={"text": "Python developer"})
    assert created.status_code == 201
    resume_id = created.json()["id"]
    assert client.get(f"/resumes/{resume_id}/matches").json() == {
        "resume_id": resume_id,
        "matches": [],
    }
    assert client.get("/resumes/9999/matches").status_code == 404
    assert client.post("/resumes", json={"text": ""}).status_code == 422