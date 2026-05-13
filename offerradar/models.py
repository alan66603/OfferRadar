import hashlib
from dataclasses import dataclass
from typing import Optional


def make_job_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


@dataclass
class JobPost:
    id: str
    source: str           # 'linkedin' | 'glassdoor' | 'indeed'
    title: str
    company: str
    location: str
    url: str
    fetched_at: str       # ISO 8601
    salary_raw: Optional[str] = None
    work_type: Optional[str] = None   # 'remote' | 'hybrid' | 'onsite'
    description: Optional[str] = None
    kw_score: Optional[float] = None
    llm_score: Optional[float] = None
    llm_reason: Optional[str] = None
    status: str = "new"
