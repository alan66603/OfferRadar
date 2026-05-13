from unittest.mock import patch, MagicMock
from offerradar.models import JobPost, make_job_id
from offerradar.page_fetcher import fetch_job_details


def _make_job(source="linkedin", url="https://www.linkedin.com/jobs/view/999/"):
    return JobPost(
        id=make_job_id(url), source=source, title="SWE", company="Acme",
        location="Taipei", url=url, fetched_at="2026-05-13T10:00:00",
    )


LINKEDIN_JOB_PAGE = """
<html><body>
<div class="description__text">
  We are looking for a Python developer with experience in AWS and Docker.
  This is a remote position. Salary: NT$1,200,000 per year.
</div>
</body></html>
"""


def test_linkedin_page_fetcher_enriches_job():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = LINKEDIN_JOB_PAGE
    with patch("offerradar.page_fetcher.requests.get", return_value=mock_resp):
        job = fetch_job_details(_make_job("linkedin"), delay=0)
    assert job.description is not None
    assert "Python" in job.description


def test_fetch_returns_original_on_http_error():
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    with patch("offerradar.page_fetcher.requests.get", return_value=mock_resp):
        original = _make_job("linkedin")
        result = fetch_job_details(original, delay=0)
    assert result.description is None
