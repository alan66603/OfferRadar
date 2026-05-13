import time
import requests
from bs4 import BeautifulSoup
from offerradar.models import JobPost

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

_DESC_SELECTORS = {
    "linkedin":  ["div.description__text", "div.show-more-less-html__markup"],
    "indeed":    ["div#jobDescriptionText", "div.jobsearch-jobDescriptionText"],
    "glassdoor": ["div.jobDescriptionContent", "div[class*='description']"],
}


def _extract_description(source: str, html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for selector in _DESC_SELECTORS.get(source, []):
        el = soup.select_one(selector)
        if el:
            return el.get_text(separator=" ", strip=True)
    return None


def fetch_job_details(job: JobPost, delay: float = 1.5) -> JobPost:
    try:
        resp = requests.get(job.url, headers=HEADERS, timeout=10)
    except requests.RequestException:
        return job

    if resp.status_code != 200:
        return job

    time.sleep(delay)
    job.description = _extract_description(job.source, resp.text)
    return job
