import email as email_lib
from unittest.mock import MagicMock, patch
from offerradar.fetcher import fetch_job_emails


def _make_mock_imap(raw_messages: list[bytes]):
    mock_imap = MagicMock()
    mock_imap.__enter__ = MagicMock(return_value=mock_imap)
    mock_imap.__exit__ = MagicMock(return_value=False)
    mock_imap.login = MagicMock()
    mock_imap.select = MagicMock(return_value=("OK", [b"1"]))
    ids = b" ".join(str(i + 1).encode() for i in range(len(raw_messages)))
    mock_imap.search = MagicMock(return_value=("OK", [ids]))
    def fetch_side_effect(num, fmt):
        idx = int(num) - 1
        return ("OK", [(b"", raw_messages[idx])])
    mock_imap.fetch = MagicMock(side_effect=fetch_side_effect)
    return mock_imap


def _make_raw_email(sender: str, html_body: str) -> bytes:
    msg = email_lib.message.Message()
    msg["From"] = sender
    msg["Subject"] = "Job Alert"
    msg.set_payload(html_body, charset="utf-8")
    msg.set_type("text/html")
    return msg.as_bytes()


def test_fetch_returns_html_from_known_senders():
    raw = _make_raw_email("jobs-noreply@linkedin.com", "<html>jobs</html>")
    mock_imap = _make_mock_imap([raw])
    with patch("offerradar.fetcher.imaplib.IMAP4_SSL", return_value=mock_imap):
        results = fetch_job_emails("imap.gmail.com", "user@gmail.com", "pass")
    assert len(results) == 1
    sender, html = results[0]
    assert "linkedin" in sender
    assert "<html>" in html


def test_fetch_filters_unknown_senders():
    raw = _make_raw_email("newsletter@random.com", "<html>ads</html>")
    mock_imap = _make_mock_imap([raw])
    # IMAP FROM-domain search returns no matches for non-job-site sender
    mock_imap.search = MagicMock(return_value=("OK", [b""]))
    with patch("offerradar.fetcher.imaplib.IMAP4_SSL", return_value=mock_imap):
        results = fetch_job_emails("imap.gmail.com", "user@gmail.com", "pass")
    assert results == []


def test_fetch_unseen_marks_emails_as_seen():
    raw = _make_raw_email("jobs-noreply@linkedin.com", "<html>jobs</html>")
    mock_imap = _make_mock_imap([raw])
    with patch("offerradar.fetcher.imaplib.IMAP4_SSL", return_value=mock_imap):
        fetch_job_emails("imap.gmail.com", "user@gmail.com", "pass", use_unseen=True)
    mock_imap.store.assert_called_once_with(b"1", "+FLAGS", "\\Seen")
