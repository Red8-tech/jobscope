import argparse

from dotenv import load_dotenv

from jobscope.ai.extractor import SkillExtractor
from jobscope.ai.llm import GroqClient
from jobscope.db.repository import JobRepository
from jobscope.services.backfill import backfill_skills


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract skills for jobs that have none.")
    parser.add_argument("--limit", type=int, default=None, help="process at most this many jobs")
    parser.add_argument("--db", default="data/jobscope.db")
    args = parser.parse_args()

    load_dotenv()
    repo = JobRepository(args.db)
    try:
        report = backfill_skills(repo, SkillExtractor(GroqClient()), limit=args.limit)
    finally:
        repo.close()
    print(f"processed {report.processed}, updated {report.updated}, failed {report.failed}")


if __name__ == "__main__":
    main()