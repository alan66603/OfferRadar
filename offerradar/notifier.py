import html
import requests
from offerradar.models import JobPost


def send_telegram(jobs: list[JobPost], bot_token: str, chat_id: str) -> None:
    if not jobs:
        return

    lines = [f"<b>OfferRadar — {len(jobs)} new job(s)</b>\n"]
    for i, job in enumerate(jobs, 1):
        score = f"{job.llm_score:.1f}" if job.llm_score is not None else "?"
        lines.append(
            f"{i}. <b>{html.escape(job.company)} — {html.escape(job.title)}</b>\n"
            f"📍 {html.escape(job.location or 'N/A')}  |  💼 {html.escape(job.work_type or 'N/A')}  |  ⭐ {score}/10\n"
            f"{html.escape(job.llm_reason or '')}\n"
            f'<a href="{job.url}">Apply →</a>'
        )

    text = "\n\n".join(lines)
    if len(text) > 4096:
        text = text[:4093] + "…"
    resp = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=10,
    )
    resp.raise_for_status()
