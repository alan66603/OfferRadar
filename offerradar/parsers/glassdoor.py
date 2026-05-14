from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from offerradar.models import JobPost, make_job_id


def parse_glassdoor_email(html: str) -> list[JobPost]:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    fetched_at = datetime.now(timezone.utc).isoformat()
    seen_ids: set[str] = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "glassdoor.com/partner/jobListing" not in href:
            continue

        qs = parse_qs(urlparse(href).query)
        job_listing_ids = qs.get("jobListingId", [])
        if not job_listing_ids:
            continue

        jid = job_listing_ids[0]
        if jid in seen_ids:
            continue
        seen_ids.add(jid)

        url = f"https://www.glassdoor.com/job-listing/j?jl={jid}"

        # Company name is in a small-font span (font-size:12px)
        company_span = a_tag.find("span", style=lambda s: s and "font-size:12px" in s)
        company = company_span.get_text(strip=True) if company_span else ""

        # Job title is in a bold paragraph (font-weight:600)
        title_p = a_tag.find("p", style=lambda s: s and "font-weight:600" in s)
        title = title_p.get_text(strip=True) if title_p else ""

        if not title:
            continue

        jobs.append(JobPost(
            id=make_job_id(url),
            source="glassdoor",
            title=title,
            company=company,
            location="",
            url=url,
            fetched_at=fetched_at,
        ))

    return jobs
