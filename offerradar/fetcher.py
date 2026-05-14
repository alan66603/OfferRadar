import imaplib
import email as email_lib
from datetime import date, timedelta

SENDER_FILTER = {
    "linkedin.com",
    "glassdoor.com",
    "indeed.com",
}


def _get_html_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
    return ""


def fetch_job_emails(
    host: str, user: str, password: str,
    days_back: int = 1, use_unseen: bool = False,
) -> list[tuple[str, str]]:
    if use_unseen:
        def _criteria(domain: str) -> str:
            return f'(UNSEEN FROM "{domain}")'
    else:
        since = (date.today() - timedelta(days=days_back)).strftime("%d-%b-%Y")
        def _criteria(domain: str) -> str:
            return f'(SINCE "{since}" FROM "{domain}")'

    results = []
    seen_ids: set[bytes] = set()
    with imaplib.IMAP4_SSL(host) as imap:
        imap.login(user, password)
        imap.select("INBOX")
        for domain in SENDER_FILTER:
            _, data = imap.search(None, _criteria(domain))
            for num in data[0].split():
                if num in seen_ids:
                    continue
                seen_ids.add(num)
                _, msg_data = imap.fetch(num, "(RFC822)")
                raw = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw)
                sender = str(msg.get("From", ""))
                html = _get_html_body(msg)
                if html:
                    results.append((sender, html))
                    if use_unseen:
                        imap.store(num, "+FLAGS", "\\Seen")
    return results
