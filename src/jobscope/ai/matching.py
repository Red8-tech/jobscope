from collections.abc import Callable

from jobscope.ai.extractor import SkillExtractor
from jobscope.ai.retrieval import Retriever, TfidfRetriever
from jobscope.models import Job, MatchResult

TEXT_WEIGHT = 0.4
SKILL_WEIGHT = 0.6

RetrieverFactory = Callable[[dict[int, str]], Retriever]


def score_job(
    text_score: float, resume_skills: set[str], job_skills: set[str]
) -> tuple[float, list[str], list[str]]:
    """Blend text similarity with skill overlap. Returns (score, matched, gaps)."""
    matched = sorted(resume_skills & job_skills)
    gaps = sorted(job_skills - resume_skills)
    if not job_skills:  # nothing to compare skills against, so rely on text alone
        return round(text_score, 4), matched, gaps
    overlap = len(matched) / len(job_skills)
    return round(TEXT_WEIGHT * text_score + SKILL_WEIGHT * overlap, 4), matched, gaps


def job_document(job: Job) -> str:
    return " ".join([job.title, *job.tags, job.description])


class ResumeMatcher:
    def __init__(
        self,
        extractor: SkillExtractor,
        retriever_factory: RetrieverFactory = TfidfRetriever,
        candidates: int = 50,
    ) -> None:
        self._extractor = extractor
        self._retriever_factory = retriever_factory
        self._candidates = candidates

    def match(self, resume_text: str, jobs: list[Job], limit: int = 10) -> list[MatchResult]:
        by_id: dict[int, Job] = {}
        for job in jobs:
            if job.id is not None:
                by_id[job.id] = job
        if not by_id or not resume_text.strip():
            return []

        resume_skills = set(self._extractor.extract(resume_text).skills)
        documents = {job_id: job_document(job) for job_id, job in by_id.items()}
        retriever = self._retriever_factory(documents)

        results = []
        for job_id, text_score in retriever.top_k(resume_text, self._candidates):
            score, matched, gaps = score_job(text_score, resume_skills, set(by_id[job_id].tags))
            results.append(MatchResult(job_id=job_id, score=score, matched=matched, gaps=gaps))
        results.sort(key=lambda r: (-r.score, r.job_id))
        return results[:limit]