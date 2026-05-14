from offerradar.models import JobPost, make_job_id


def test_make_job_id_is_deterministic():
    url = "https://www.linkedin.com/jobs/view/12345"
    assert make_job_id(url) == make_job_id(url)


def test_make_job_id_is_16_chars():
    assert len(make_job_id("https://example.com/job/1")) == 16


def test_jobpost_defaults():
    job = JobPost(
        id="abc123",
        source="linkedin",
        title="ML Engineer",
        company="Acme",
        location="Taipei",
        url="https://linkedin.com/jobs/view/1",
        fetched_at="2026-05-13T16:23:00",
    )
    assert job.status == "new"
    assert job.description is None
    assert job.kw_score is None
