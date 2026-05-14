from datetime import datetime, timezone
from bs4 import BeautifulSoup
from offerradar.models import JobPost, make_job_id


def parse_indeed_email(html: str) -> list[JobPost]:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    fetched_at = datetime.now(timezone.utc).isoformat()

    for row in soup.find_all("tr"):
        a_tag = row.find("a", href=True)
        if not a_tag or "indeed.com" not in a_tag.get("href", ""):
            continue
        title = a_tag.get_text(strip=True)
        url = a_tag["href"].split("?")[0]
        cells = row.find_all("td")
        company = cells[1].get_text(strip=True) if len(cells) > 1 else ""
        location = cells[2].get_text(strip=True) if len(cells) > 2 else ""

        jobs.append(JobPost(
            id=make_job_id(url),
            source="indeed",
            title=title,
            company=company,
            location=location,
            url=url,
            fetched_at=fetched_at,
        ))
    return jobs
