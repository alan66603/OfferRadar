import sqlite3
from offerradar.models import JobPost


class JobRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id          TEXT PRIMARY KEY,
                    source      TEXT,
                    title       TEXT,
                    company     TEXT,
                    location    TEXT,
                    salary_raw  TEXT,
                    work_type   TEXT,
                    url         TEXT,
                    fetched_at  TEXT,
                    description TEXT,
                    kw_score    REAL,
                    llm_score   REAL,
                    llm_reason  TEXT,
                    status      TEXT DEFAULT 'new'
                )
            """)

    def exists(self, job_id: str) -> bool:
        with self._conn() as conn:
            row = conn.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return row is not None

    def save(self, job: JobPost) -> None:
        with self._conn() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO jobs
                (id, source, title, company, location, salary_raw, work_type,
                 url, fetched_at, description, kw_score, llm_score, llm_reason, status)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (job.id, job.source, job.title, job.company, job.location,
                  job.salary_raw, job.work_type, job.url, job.fetched_at,
                  job.description, job.kw_score, job.llm_score, job.llm_reason, job.status))

    def get(self, job_id: str) -> JobPost:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        cols = ["id", "source", "title", "company", "location", "salary_raw", "work_type",
                "url", "fetched_at", "description", "kw_score", "llm_score", "llm_reason", "status"]
        return JobPost(**dict(zip(cols, row)))

    def update_scores(self, job_id: str, kw_score: float, llm_score: float, llm_reason: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE jobs SET kw_score=?, llm_score=?, llm_reason=? WHERE id=?",
                (kw_score, llm_score, llm_reason, job_id),
            )

    def mark_sent(self, job_ids: list[str]) -> None:
        with self._conn() as conn:
            conn.executemany(
                "UPDATE jobs SET status='sent' WHERE id=?",
                [(jid,) for jid in job_ids],
            )
