from collections.abc import Callable
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


def create_app(
    db_path: str | Path = DEFAULT_DB,
    sources: dict[str, SourceFactory] | None = None,
    matcher_factory: MatcherFactory = default_matcher,
) -> FastAPI:
    app = FastAPI(title="jobscope", version=__version__)
    app.state.db_path = Path(db_path)
    app.state.sources = default_sources() if sources is None else sources
    app.state.matcher_factory = matcher_factory
    app.include_router(router)
    return app