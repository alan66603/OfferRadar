import html
import requests
from offerradar.models import JobPost


def send_telegram(jobs: list[JobPost], bot_token: str, chat_id: str) -> None:
    for job in jobs:
        score = f"{job.llm_score:.1f}" if job.llm_score is not None else "?"
        text = (
            f"<b>{html.escape(job.company)} — {html.escape(job.title)}</b>\n"
            f"📍 {html.escape(job.location or 'N/A')}  |  💼 {html.escape(job.work_type or 'N/A')}\n"
            f"⭐ Score: {score}/10\n"
            f"{html.escape(job.llm_reason or '')}\n"
            f'<a href="{job.url}">Apply →</a>'
        )
        resp = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        resp.raise_for_status()
