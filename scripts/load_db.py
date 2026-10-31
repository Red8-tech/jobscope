from jobscope.db.repository import JobRepository
from jobscope.ingestion.csv_source import CsvSource


def main() -> None:
    jobs = CsvSource("data/sample/messy_jobs.csv").fetch()
    repo = JobRepository("data/jobscope.db")
    added = repo.add_jobs(jobs)
    print(f"added {added} new jobs, {repo.count_jobs()} total")
    print("top skills:")
    for skill in repo.top_skills(5):
        print(f"  {skill.name}: {skill.jobs}")
    print("top companies:")
    for company in repo.top_companies(5):
        print(f"  #{company.position} {company.company}: {company.jobs}")
    repo.close()


if __name__ == "__main__":
    main()