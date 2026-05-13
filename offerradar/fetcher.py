import imaplib
import email as email_lib

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


def fetch_job_emails(host: str, user: str, password: str) -> list[tuple[str, str]]:
    results = []
    with imaplib.IMAP4_SSL(host) as imap:
        imap.login(user, password)
        imap.select("INBOX")
        _, data = imap.search(None, "UNSEEN")
        ids = data[0].split()
        for num in ids:
            _, msg_data = imap.fetch(num, "(RFC822)")
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)
            sender = str(msg.get("From", ""))
            if any(domain in sender for domain in SENDER_FILTER):
                html = _get_html_body(msg)
                if html:
                    results.append((sender, html))
    return results
