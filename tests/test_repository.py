import pytest
from offerradar.models import JobPost
from offerradar.repository import JobRepository


@pytest.fixture
def repo(tmp_path):
    return JobRepository(str(tmp_path / "test.db"))


def _make_job(job_id="abc1", url="https://example.com/1"):
    return JobPost(
        id=job_id, source="linkedin", title="SWE", company="Acme",
        location="Taipei", url=url, fetched_at="2026-05-13T10:00:00",
    )


def test_exists_returns_false_for_new_job(repo):
    assert repo.exists("nonexistent") is False


def test_save_and_exists(repo):
    job = _make_job()
    repo.save(job)
    assert repo.exists(job.id) is True


def test_save_duplicate_is_idempotent(repo):
    job = _make_job()
    repo.save(job)
    repo.save(job)  # should not raise
    assert repo.exists(job.id) is True


def test_update_scores(repo):
    job = _make_job()
    repo.save(job)
    repo.update_scores(job.id, kw_score=0.8, llm_score=7.5, llm_reason="Good fit.")
    updated = repo.get(job.id)
    assert updated.kw_score == 0.8
    assert updated.llm_score == 7.5
    assert updated.llm_reason == "Good fit."


def test_mark_sent(repo):
    j1 = _make_job("id1", "https://a.com/1")
    j2 = _make_job("id2", "https://a.com/2")
    repo.save(j1)
    repo.save(j2)
    repo.mark_sent(["id1", "id2"])
    assert repo.get("id1").status == "sent"
    assert repo.get("id2").status == "sent"
