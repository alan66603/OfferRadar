from unittest.mock import patch, MagicMock
from offerradar.models import JobPost
from offerradar.digest import compose_html, send_digest


def _scored_job(job_id, score=8.0):
    return JobPost(
        id=job_id, source="linkedin", title="ML Engineer", company="Qualcomm",
        location="Hsinchu City", url=f"https://linkedin.com/jobs/view/{job_id}/",
        fetched_at="2026-05-13T10:00:00",
        work_type="remote", salary_raw="NT$1,200,000",
        llm_score=score, llm_reason="Strong Python and ML skills match.",
    )


def test_compose_html_contains_job_info():
    html = compose_html([_scored_job("j1")])
    assert "ML Engineer" in html
    assert "Qualcomm" in html
    assert "Hsinchu City" in html
    assert "8.0" in html
    assert "Strong Python" in html
    assert "https://linkedin.com/jobs/view/j1/" in html


def test_compose_html_sorts_by_score():
    jobs = [_scored_job("j1", score=6.0), _scored_job("j2", score=9.0)]
    html = compose_html(jobs)
    assert html.index("j2") < html.index("j1")


def test_send_digest_calls_smtp():
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)

    with patch("offerradar.digest.smtplib.SMTP", return_value=mock_smtp):
        send_digest(
            html="<html>test</html>",
            to_email="user@gmail.com",
            smtp_config={
                "host": "smtp.gmail.com", "port": 587,
                "user": "sender@gmail.com", "password": "pass",
            },
        )

    mock_smtp.starttls.assert_called_once()
    mock_smtp.login.assert_called_once()
    mock_smtp.send_message.assert_called_once()
