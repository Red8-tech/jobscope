SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    url TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    job_type TEXT NOT NULL DEFAULT '',
    location TEXT NOT NULL DEFAULT '',
    salary_text TEXT NOT NULL DEFAULT '',
    salary_min REAL,
    salary_max REAL,
    salary_currency TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    posted_at TEXT,
    UNIQUE (source, source_id)
);

CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS job_skills (
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, skill_id)
);

CREATE TABLE IF NOT EXISTS resumes (
    id INTEGER PRIMARY KEY,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY,
    resume_id INTEGER NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    score REAL NOT NULL,
    matched TEXT NOT NULL DEFAULT '[]',
    gaps TEXT NOT NULL DEFAULT '[]',
    UNIQUE (resume_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_job_skills_skill ON job_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_jobs_posted ON jobs(posted_at);
"""