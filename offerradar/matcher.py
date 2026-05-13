import json
import anthropic
from offerradar.models import JobPost

_SYSTEM_PROMPT = (
    "You are a job matching assistant. Given a candidate's resume and a job posting, "
    "score how well the candidate fits the job. "
    'Respond with valid JSON only: {"score": <float 0-10>, "reason": "<one sentence>"}'
)


def _kw_score(text: str, keywords: list[str]) -> float:
    if not keywords or not text:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in text_lower)
    return round(hits / len(keywords), 3)


def layer1_filter(jobs: list[JobPost], resume_keywords: list[str], prefs: dict) -> list[JobPost]:
    threshold = prefs.get("kw_score_threshold", 0.2)
    allowed_locations = {loc.lower() for loc in prefs.get("locations", [])}
    allowed_work_types = {wt.lower() for wt in prefs.get("work_types", [])}

    passed = []
    for job in jobs:
        if allowed_locations and job.location:
            if not any(loc in job.location.lower() for loc in allowed_locations):
                continue

        if job.work_type and allowed_work_types:
            if job.work_type.lower() not in allowed_work_types:
                continue

        search_text = (job.description or "") + " " + job.title
        score = _kw_score(search_text, resume_keywords)
        if score < threshold:
            continue

        job.kw_score = score
        passed.append(job)

    return passed


def layer2_score(jobs: list[JobPost], resume_text: str, prefs: dict) -> list[JobPost]:
    client = anthropic.Anthropic()
    for job in jobs[:20]:
        job_summary = (
            f"Title: {job.title}\n"
            f"Company: {job.company}\n"
            f"Location: {job.location}\n"
            f"Work type: {job.work_type or 'unknown'}\n"
            f"Description: {(job.description or '')[:1500]}"
        )
        user_msg = (
            f"RESUME (excerpt):\n{resume_text[:1000]}\n\n"
            f"JOB:\n{job_summary}\n\n"
            f"PREFERENCES:\n"
            f"  Must-have keywords: {prefs.get('keywords_must', [])}\n"
            f"  Nice-to-have keywords: {prefs.get('keywords_nice', [])}\n"
            f"  Visa sponsorship required: {prefs.get('visa_sponsorship_required', False)}"
        )
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        try:
            result = json.loads(message.content[0].text)
            job.llm_score = float(result.get("score", 0))
            job.llm_reason = result.get("reason", "")
        except (json.JSONDecodeError, KeyError, IndexError):
            job.llm_score = 0.0
            job.llm_reason = ""
    return jobs
