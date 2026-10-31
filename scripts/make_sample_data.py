"""Generate a deliberately messy, synthetic job dataset for development and tests."""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
N_JOBS = 300
OUTPUT = Path("data/sample/messy_jobs.csv")


SKILLS = [
    "python", "sql", "fastapi", "django", "flask", "pandas", "docker", "aws",
    "react", "postgresql", "pytest", "git", "kubernetes", "redis", "langchain",
]
TITLES = [
    "Python Developer", "Backend Engineer", "Data Analyst", "Data Engineer",
    "Full Stack Developer", "ML Engineer", "DevOps Engineer", "QA Automation Engineer",
]
COMPANIES = [
    "Acme", "Globex", "Initech", "Umbrella", "Hooli",
    "Vandelay", "Stark Systems", "Wayne Tech", "Wonka Labs", "Cyberdyne",
]
LOCATIONS = [
    "Remote", "remote", "Worldwide", "Anywhere", "USA Only", "US",
    "United States", "EU", "Europe", "", "India", "UK",
]
SALARIES = [
    "$90,000", "90k-120k", "€70k", "$50/hour", "competitive", "",
    "$110,000 - $140,000", "£55k",
]
CATEGORIES = ["Software Development", "Data", "DevOps", "QA"]
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y", "%Y-%m-%dT%H:%M:%S"]



def make_row(rng: random.Random, index: int) -> dict[str, str]:
    skills = rng.sample(SKILLS, k=rng.randint(2, 5))
    title = rng.choice(TITLES)
    company = rng.choice(COMPANIES)
    posted = date(2026, 10, 28) - timedelta(days=rng.randint(0, 60))
    separator = rng.choice([",", "|", "; "])
    tags = separator.join(s.title() if rng.random() < 0.3 else s for s in skills)
    job_id = str(1000 + index)
    return {
        "id": job_id,
        "title": "" if rng.random() < 0.01 else title,
        "company": rng.choice([company, company.upper(), f"  {company} ", company.lower()]),
        "location": rng.choice(LOCATIONS),
        "salary": rng.choice(SALARIES),
        "posted": posted.strftime(rng.choice(DATE_FORMATS)),
        "tags": "" if rng.random() < 0.1 else tags,
        "description": (
            f"<p>We need a {title} skilled in <b>{skills[0]}</b> and {skills[1]} "
            f"&amp; more.</p><ul><li>Experience with {skills[-1]}</li></ul>"
        ),
        "url": f"https://example.com/jobs/{job_id}",
        "category": rng.choice(CATEGORIES),
    }



def build_rows() -> list[dict[str, str]]:
    rng = random.Random(SEED)
    rows = [make_row(rng, i) for i in range(N_JOBS)]
    exact_duplicates = [dict(row) for row in rng.sample(rows, k=15)]
    reposts = []
    for offset, row in enumerate(rng.sample(rows, k=15)):
        repost = dict(row)
        repost["id"] = str(5000 + offset)
        repost["company"] = repost["company"].upper()
        reposts.append(repost)
    combined = rows + exact_duplicates + reposts
    rng.shuffle(combined)
    return combined



def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUTPUT}")



if __name__ == "__main__":
    main()