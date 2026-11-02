from collections.abc import Callable, Mapping
from pathlib import Path

from fastapi import FastAPI

from jobscope import __version__
from jobscope.ai.extractor import SkillExtractor
from jobscope.ai.llm import GroqClient
from jobscope.ai.matching import ResumeMatcher
from jobscope.api.routes import router
from jobscope.ingestion.csv_source import CsvSource
from jobscope.ingestion.remotive import RemotiveSource
from jobscope.ingestion.sources import JobSource

DEFAULT_DB = Path("data/jobscope.db")
DEFAULT_CSV = Path("data/sample/messy_jobs.csv")

SourceFactory = Callable[[], JobSource]
MatcherFactory = Callable[[], ResumeMatcher]


def default_sources() -> dict[str, SourceFactory]:
    return {"csv": lambda: CsvSource(DEFAULT_CSV), "remotive": RemotiveSource}


def default_matcher() -> ResumeMatcher:
    return ResumeMatcher(SkillExtractor(GroqClient()))


ExtractorFactory = Callable[[], SkillExtractor]


def default_extractor() -> SkillExtractor:
    return SkillExtractor(GroqClient())


def create_app(
    db_path: str | Path = DEFAULT_DB,
    sources: dict[str, SourceFactory] | None = None,
    matcher_factory: MatcherFactory = default_matcher,
    api_key: str | None = None,
    extractor_factory: ExtractorFactory = default_extractor,
) -> FastAPI:
    app = FastAPI(title="jobscope", version=__version__)
    app.state.db_path = Path(db_path)
    app.state.sources = default_sources() if sources is None else sources
    app.state.matcher_factory = matcher_factory
    app.state.api_key = api_key
    app.state.extractor_factory = extractor_factory
    app.include_router(router)
    return app


def create_app_from_env(env: Mapping[str, str]) -> FastAPI:
    """Build the app from environment settings, failing closed in production."""
    api_key = env.get("JOBSCOPE_API_KEY") or None
    if env.get("JOBSCOPE_ENV") == "production" and api_key is None:
        raise RuntimeError("JOBSCOPE_API_KEY must be set when JOBSCOPE_ENV=production")
    return create_app(db_path=env.get("JOBSCOPE_DB", str(DEFAULT_DB)), api_key=api_key)