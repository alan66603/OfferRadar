from unittest.mock import patch, MagicMock
from offerradar.notifier import send_telegram
from offerradar.models import JobPost


def _make_job():
    return JobPost(
        id="abc123", source="linkedin", title="ML Engineer",
        company="Google", location="Taipei",
        url="https://www.linkedin.com/jobs/view/1/",
        fetched_at="2026-05-14T00:00:00+00:00",
        llm_score=8.5, llm_reason="Strong Python match.",
    )


def test_send_telegram_posts_one_message_per_job():
    with patch("offerradar.notifier.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        send_telegram([_make_job(), _make_job()], bot_token="TOKEN", chat_id="123")
    assert mock_post.call_count == 2


def test_send_telegram_empty_list_makes_no_calls():
    with patch("offerradar.notifier.requests.post") as mock_post:
        send_telegram([], bot_token="TOKEN", chat_id="123")
    mock_post.assert_not_called()


def test_send_telegram_message_contains_title_and_score():
    with patch("offerradar.notifier.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        send_telegram([_make_job()], bot_token="TOKEN", chat_id="123")
    payload = mock_post.call_args.kwargs["json"]
    assert "ML Engineer" in payload["text"]
    assert "8.5" in payload["text"]
    assert payload["chat_id"] == "123"
