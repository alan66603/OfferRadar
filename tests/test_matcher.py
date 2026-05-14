from unittest.mock import patch, MagicMock
from offerradar.models import JobPost
from offerradar.matcher import layer1_filter, layer2_score


def _job(job_id, title="ML Engineer", description="Python AWS machine learning",
         location="Hsinchu", work_type="remote"):
    return JobPost(
        id=job_id, source="linkedin", title=title, company="Acme",
        location=location, url=f"https://example.com/{job_id}",
        fetched_at="2026-05-13T10:00:00",
        description=description, work_type=work_type,
    )


PREFS = {
    "locations": ["Hsinchu", "Remote"],
    "work_types": ["remote", "hybrid"],
    "job_type": "internship",
    "keywords_must": ["Python", "Machine Learning"],
    "keywords_nice": ["AWS", "PyTorch"],
    "kw_score_threshold": 0.2,
    "visa_sponsorship_required": False,
    "salary_min_twd": None,
}


def test_layer1_passes_matching_job():
    jobs = [_job("j1")]
    passed = layer1_filter(jobs, ["Python", "Machine Learning", "AWS"], PREFS)
    assert len(passed) == 1
    assert passed[0].kw_score > 0.2


def test_layer1_rejects_wrong_location():
    jobs = [_job("j2", location="Tokyo")]
    passed = layer1_filter(jobs, ["Python", "Machine Learning"], PREFS)
    assert passed == []


def test_layer1_rejects_wrong_work_type():
    job = _job("j3", work_type="onsite")
    passed = layer1_filter([job], ["Python", "Machine Learning"], PREFS)
    assert passed == []


def test_layer1_passes_when_work_type_unknown():
    job = _job("j4")
    job.work_type = None
    passed = layer1_filter([job], ["Python", "Machine Learning"], PREFS)
    assert len(passed) == 1


def test_layer2_score_calls_claude_and_sets_scores(mocker):
    jobs = [_job("j5")]
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text='{"score": 8.0, "reason": "Great fit."}')]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("offerradar.matcher.anthropic.Anthropic", return_value=mock_client):
        scored = layer2_score(jobs, resume_text="Python developer with AWS exp.", prefs=PREFS)

    assert scored[0].llm_score == 8.0
    assert scored[0].llm_reason == "Great fit."
