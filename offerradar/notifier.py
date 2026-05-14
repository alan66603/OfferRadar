import requests
from offerradar.models import JobPost


def send_telegram(jobs: list[JobPost], bot_token: str, chat_id: str) -> None:
    for job in jobs:
        score = f"{job.llm_score:.1f}" if job.llm_score is not None else "?"
        text = (
            f"*{job.company} — {job.title}*\n"
            f"📍 {job.location or 'N/A'}  |  💼 {job.work_type or 'N/A'}\n"
            f"⭐ Score: {score}/10\n"
            f"{job.llm_reason or ''}\n"
            f"[Apply →]({job.url})"
        )
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
