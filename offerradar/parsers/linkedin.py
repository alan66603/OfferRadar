import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from offerradar.models import JobPost, make_job_id

_JOB_ID_RE = re.compile(r'/jobs/view/(\d+)')


def _extract_clean_url(href: str) -> str | None:
    match = _JOB_ID_RE.search(href)
    if not match:
        return None
    return f"https://www.linkedin.com/jobs/view/{match.group(1)}/"


def parse_linkedin_email(html: str) -> list[JobPost]:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    fetched_at = datetime.now(timezone.utc).isoformat()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "linkedin.com" not in href or "/jobs/view/" not in href:
            continue
        title = a_tag.get_text(strip=True)
        if not title:
            continue

        url = _extract_clean_url(href)
        if not url:
            continue

        parent = a_tag.parent
        text = parent.get_text(separator="\n", strip=True)
        lines = [l for l in text.splitlines() if l and l != title]

        company, location = "", ""
        if lines:
            first = lines[0]
            if "·" in first:
                parts = first.split("·", 1)
                company = parts[0].strip()
                location = parts[1].strip()
            else:
                company = first
                location = lines[1] if len(lines) > 1 else ""

        jobs.append(JobPost(
            id=make_job_id(url),
            source="linkedin",
            title=title,
            company=company,
            location=location,
            url=url,
            fetched_at=fetched_at,
        ))
    return jobs
