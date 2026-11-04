import argparse
import json
from pathlib import Path

from jobscope.db.repository import JobRepository


def main() -> None:
    parser = argparse.ArgumentParser(description="Export job skills for use as a startup seed.")
    parser.add_argument("--db", default="data/jobscope.db")
    parser.add_argument("--out", default="data/sample/skills_snapshot.json")
    args = parser.parse_args()

    repo = JobRepository(args.db)
    try:
        snapshot = {
            job.source_id: sorted(job.tags)
            for job in repo.all_jobs()
            if job.tags and job.source == "csv"
        }
    finally:
        repo.close()
    Path(args.out).write_text(json.dumps(snapshot, indent=1, sort_keys=True), encoding="utf-8")
    print(f"wrote skills for {len(snapshot)} jobs to {args.out}")


if __name__ == "__main__":
    main()