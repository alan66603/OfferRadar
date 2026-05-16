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

    seen_urls: set[str] = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "linkedin.com" not in href or "/jobs/view/" not in href:
            continue

        url = _extract_clean_url(href)
        if not url or url in seen_urls:
            continue

        # Use only the first non-empty line as title to avoid capturing
        # company/location/badge text that may be nested inside the same anchor
        raw_text = a_tag.get_text(separator="\n", strip=True)
        title = next((l for l in raw_text.splitlines() if l), "")
        if not title:
            continue

        seen_urls.add(url)

        parent = a_tag.parent
        parent_text = parent.get_text(separator="\n", strip=True)
        lines = [l for l in parent_text.splitlines() if l and l != title]

        company, location = "", ""
        for line in lines:
            if "·" in line:
                parts = line.split("·", 1)
                company = parts[0].strip()
                location = parts[1].strip()
                break
            # skip badge-like lines (short words, no spaces typical of real company names)
            if len(line.split()) >= 2:
                company = line
                break

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
