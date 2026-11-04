from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from jobscope import __version__
from jobscope.ai.extractor import SkillExtractor
from jobscope.ai.llm import GroqClient
from jobscope.ai.matching import ResumeMatcher
from jobscope.api.routes import router
from jobscope.db.repository import JobRepository
from jobscope.ingestion.csv_source import CsvSource
from jobscope.ingestion.remotive import RemotiveSource
from jobscope.ingestion.sources import JobSource
from jobscope.services.seed import seed_if_empty

DEFAULT_DB = Path("data/jobscope.db")
DEFAULT_CSV = Path("data/sample/messy_jobs.csv")
DEFAULT_SNAPSHOT = Path("data/sample/skills_snapshot.json")

SourceFactory = Callable[[], JobSource]
MatcherFactory = Callable[[], ResumeMatcher]
ExtractorFactory = Callable[[], SkillExtractor]


def default_sources() -> dict[str, SourceFactory]:
    return {"csv": lambda: CsvSource(DEFAULT_CSV), "remotive": RemotiveSource}


def default_matcher() -> ResumeMatcher:
    return ResumeMatcher(SkillExtractor(GroqClient()))


def default_extractor() -> SkillExtractor:
    return SkillExtractor(GroqClient())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if app.state.seed_on_startup:
        repo = JobRepository(app.state.db_path)
        try:
            seed_if_empty(repo, app.state.sources["csv"](), app.state.skills_snapshot)
        finally:
            repo.close()
    yield


def create_app(
    db_path: str | Path = DEFAULT_DB,
    sources: dict[str, SourceFactory] | None = None,
    matcher_factory: MatcherFactory = default_matcher,
    api_key: str | None = None,
    extractor_factory: ExtractorFactory = default_extractor,
    seed_on_startup: bool = False,
    skills_snapshot: Path | None = DEFAULT_SNAPSHOT,
) -> FastAPI:
    app = FastAPI(title="jobscope", version=__version__, lifespan=lifespan)
    app.state.db_path = Path(db_path)
    app.state.sources = default_sources() if sources is None else sources
    app.state.matcher_factory = matcher_factory
    app.state.api_key = api_key
    app.state.extractor_factory = extractor_factory
    app.state.seed_on_startup = seed_on_startup
    app.state.skills_snapshot = skills_snapshot
    app.include_router(router)
    return app


def create_app_from_env(env: Mapping[str, str]) -> FastAPI:
    """Build the app from environment settings, failing closed in production."""
    api_key = env.get("JOBSCOPE_API_KEY") or None
    if env.get("JOBSCOPE_ENV") == "production" and api_key is None:
        raise RuntimeError("JOBSCOPE_API_KEY must be set when JOBSCOPE_ENV=production")
    return create_app(
        db_path=env.get("JOBSCOPE_DB", str(DEFAULT_DB)),
        api_key=api_key,
        seed_on_startup=env.get("JOBSCOPE_SEED") == "1",
    )