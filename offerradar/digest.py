import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date
from offerradar.models import JobPost


def compose_html(jobs: list[JobPost]) -> str:
    sorted_jobs = sorted(jobs, key=lambda j: j.llm_score or 0, reverse=True)
    cards = []
    for job in sorted_jobs:
        work = job.work_type or "N/A"
        salary = job.salary_raw or "N/A"
        score = f"{job.llm_score:.1f}" if job.llm_score is not None else "N/A"
        reason = job.llm_reason or ""
        cards.append(
            f'<div style="border:1px solid #ddd;border-radius:8px;padding:16px;margin-bottom:16px;">'
            f'<h3 style="margin:0 0 4px">{job.company} — {job.title}</h3>'
            f'<p style="margin:4px 0;color:#555;">📍 {job.location} &nbsp;|&nbsp; 💼 {work} &nbsp;|&nbsp; 💰 {salary}</p>'
            f'<p style="margin:4px 0;">⭐ Score: <strong>{score}/10</strong></p>'
            f'<p style="margin:4px 0;color:#333;">{reason}</p>'
            f'<a href="{job.url}" style="display:inline-block;margin-top:8px;background:#0a66c2;'
            f'color:#fff;padding:6px 14px;border-radius:4px;text-decoration:none;">Apply →</a>'
            f'</div>'
        )
    today = date.today().strftime("%Y-%m-%d")
    body = "\n".join(cards) if cards else "<p>No new matching jobs today.</p>"
    return (
        f"<html><body style='font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px;'>"
        f"<h2>OfferRadar — {today}</h2>"
        f"<p>{len(sorted_jobs)} job(s) matched your profile today.</p>"
        f"{body}</body></html>"
    )


def send_digest(html: str, to_email: str, smtp_config: dict) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"OfferRadar Digest — {date.today().strftime('%Y-%m-%d')}"
    msg["From"] = smtp_config["user"]
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
        server.starttls()
        server.login(smtp_config["user"], smtp_config["password"])
        server.send_message(msg)
