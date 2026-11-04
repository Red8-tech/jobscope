from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from jobscope.ai.extractor import SkillExtractor
from jobscope.ai.llm import LLMError
from jobscope.ai.matching import ResumeMatcher
from jobscope.api.app import create_app, create_app_from_env
from jobscope.ingestion.remotive import IngestionError
from jobscope.models import Job
from tests.fakes import ScriptedClient


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



@pytest.fixture
def match_client(tmp_path: Path) -> Iterator[TestClient]:
    llm = ScriptedClient(['{"skills": ["python", "sql"], "seniority": "mid"}'])
    app = create_app(
        db_path=tmp_path / "match.db",
        sources={"fake": FakeSource},
        matcher_factory=lambda: ResumeMatcher(SkillExtractor(llm)),
    )
    with TestClient(app) as test_client:
        yield test_client


def test_match_flow_scores_stores_and_returns_matches(match_client: TestClient) -> None:
    ingest_fake(match_client)
    resume_id = match_client.post("/resumes", json={"text": "Python developer, SQL"}).json()["id"]

    matched = match_client.post(f"/resumes/{resume_id}/match").json()
    assert matched["matches"][0]["job_id"] == 1
    assert matched["matches"][0]["gaps"] == []

    stored = match_client.get(f"/resumes/{resume_id}/matches").json()
    assert stored == matched


def test_match_unknown_resume_is_404(match_client: TestClient) -> None:
    assert match_client.post("/resumes/9999/match").status_code == 404


def raise_llm_error() -> ResumeMatcher:
    raise LLMError("GROQ_API_KEY is not set")


def test_match_returns_503_when_ai_is_unavailable(tmp_path: Path) -> None:
    app = create_app(db_path=tmp_path / "x.db", matcher_factory=raise_llm_error)
    with TestClient(app) as test_client:
        resume_id = test_client.post("/resumes", json={"text": "Python"}).json()["id"]
        response = test_client.post(f"/resumes/{resume_id}/match")
    assert response.status_code == 503
    assert "GROQ_API_KEY" in response.json()["detail"]


@pytest.fixture
def secured_client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(
        db_path=tmp_path / "secured.db", sources={"fake": FakeSource}, api_key="secret"
    )
    with TestClient(app) as test_client:
        yield test_client


def test_protected_routes_reject_missing_or_wrong_key(secured_client: TestClient) -> None:
    wrong = {"X-API-Key": "nope"}
    params = {"source": "fake"}
    assert secured_client.post("/ingest", params=params).status_code == 401
    assert secured_client.post("/ingest", params=params, headers=wrong).status_code == 401
    assert secured_client.post("/resumes", json={"text": "x"}).status_code == 401
    assert secured_client.get("/resumes/1/matches").status_code == 401


def test_correct_key_is_accepted(secured_client: TestClient) -> None:
    headers = {"X-API-Key": "secret"}
    params = {"source": "fake"}
    assert secured_client.post("/ingest", params=params, headers=headers).status_code == 200
    assert secured_client.post("/resumes", json={"text": "x"}, headers=headers).status_code == 201


def test_read_only_routes_stay_public(secured_client: TestClient) -> None:
    for path in ("/health", "/jobs", "/skills/trending"):
        assert secured_client.get(path).status_code == 200


def test_production_refuses_to_start_without_api_key(tmp_path: Path) -> None:
    env = {"JOBSCOPE_ENV": "production", "JOBSCOPE_DB": str(tmp_path / "p.db")}
    with pytest.raises(RuntimeError, match="JOBSCOPE_API_KEY"):
        create_app_from_env(env)


def test_production_with_api_key_starts(tmp_path: Path) -> None:
    env = {
        "JOBSCOPE_ENV": "production",
        "JOBSCOPE_API_KEY": "k",
        "JOBSCOPE_DB": str(tmp_path / "p.db"),
    }
    assert create_app_from_env(env).state.api_key == "k"


class UntaggedSource:
    name = "untagged"

    def fetch(self) -> list[Job]:
        return [
            Job(source="u", source_id="1", title="Dev", company="Acme", url="u",
                description="needs redis")
        ]


def test_backfill_fills_untagged_jobs(tmp_path: Path) -> None:
    llm = ScriptedClient(['{"skills": ["redis"]}'])
    app = create_app(
        db_path=tmp_path / "b.db",
        sources={"untagged": UntaggedSource},
        extractor_factory=lambda: SkillExtractor(llm),
    )
    with TestClient(app) as test_client:
        test_client.post("/ingest", params={"source": "untagged"})
        result = test_client.post("/backfill").json()
        job = test_client.get("/jobs/1").json()
    assert result == {"processed": 1, "updated": 1, "failed": 0}
    assert job["tags"] == ["redis"]


def test_backfill_requires_api_key(tmp_path: Path) -> None:
    app = create_app(db_path=tmp_path / "b.db", api_key="secret")
    with TestClient(app) as test_client:
        assert test_client.post("/backfill").status_code == 401


def test_backfill_returns_503_when_ai_is_unavailable(tmp_path: Path) -> None:
    def broken() -> SkillExtractor:
        raise LLMError("GROQ_API_KEY is not set")

    app = create_app(db_path=tmp_path / "b.db", extractor_factory=broken)
    with TestClient(app) as test_client:
        assert test_client.post("/backfill").status_code == 503


def test_app_seeds_an_empty_database_on_startup(tmp_path: Path) -> None:
    app = create_app(
        db_path=tmp_path / "seed.db",
        sources={"csv": FakeSource},
        seed_on_startup=True,
        skills_snapshot=None,
    )
    with TestClient(app) as test_client:
        assert test_client.get("/jobs").json()["total"] == 3


def test_seed_flag_comes_from_environment(tmp_path: Path) -> None:
    env = {"JOBSCOPE_DB": str(tmp_path / "e.db"), "JOBSCOPE_SEED": "1"}
    assert create_app_from_env(env).state.seed_on_startup is True