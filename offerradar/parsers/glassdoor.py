from datetime import datetime, timezone
from bs4 import BeautifulSoup
from offerradar.models import JobPost, make_job_id


def parse_glassdoor_email(html: str) -> list[JobPost]:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    fetched_at = datetime.now(timezone.utc).isoformat()

    for div in soup.find_all("div", class_="job-listing"):
        a_tag = div.find("a", href=True)
        if not a_tag:
            continue
        title = a_tag.get_text(strip=True)
        url = a_tag["href"].split("?")[0]

        employer = div.find(class_="employer-name")
        loc = div.find(class_="location")
        company = employer.get_text(strip=True) if employer else ""
        location = loc.get_text(strip=True) if loc else ""

        jobs.append(JobPost(
            id=make_job_id(url),
            source="glassdoor",
            title=title,
            company=company,
            location=location,
            url=url,
            fetched_at=fetched_at,
        ))
    return jobs
