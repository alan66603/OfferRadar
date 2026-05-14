import json
import re
import anthropic
from offerradar.models import JobPost

_SYSTEM_PROMPT = (
    "You are a job matching assistant. Given a candidate's resume and a job posting, "
    "score how well the candidate fits the job. "
    'Respond with valid JSON only: {"score": <float 0-10>, "reason": "<one sentence>"}'
)


_EXP_RE = re.compile(r'(\d+)\+?\s*(?:to\s*\d+\s*)?years?', re.IGNORECASE)


def _kw_score(text: str, keywords: list[str]) -> float:
    if not keywords or not text:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in text_lower)
    return round(hits / len(keywords), 3)


def _exceeds_experience(text: str, max_years: int) -> bool:
    for m in _EXP_RE.finditer(text):
        if int(m.group(1)) >= max_years:
            return True
    return False


def layer1_filter(jobs: list[JobPost], resume_keywords: list[str], prefs: dict) -> list[JobPost]:
    threshold = prefs.get("kw_score_threshold", 0.2)
    allowed_locations = {loc.lower() for loc in prefs.get("locations", [])}
    allowed_work_types = {wt.lower() for wt in prefs.get("work_types", [])}
    max_exp = prefs.get("max_years_experience")
    exclude_kws = [kw.lower() for kw in prefs.get("keywords_exclude", [])]

    passed = []
    for job in jobs:
        if allowed_locations and job.location:
            if not any(loc in job.location.lower() for loc in allowed_locations):
                continue

        if job.work_type and allowed_work_types:
            if job.work_type.lower() not in allowed_work_types:
                continue

        search_text = (job.description or "") + " " + job.title
        if max_exp is not None and _exceeds_experience(search_text, max_exp):
            continue

        search_lower = search_text.lower()
        if any(kw in search_lower for kw in exclude_kws):
            continue

        score = _kw_score(search_text, resume_keywords)
        if score < threshold:
            continue

        job.kw_score = score
        passed.append(job)

    return passed


def _parse_llm_response(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # model may wrap JSON in markdown or add surrounding text
    m = re.search(r'\{[^{}]*"score"[^{}]*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    print(f"  [warn] Unparseable Claude response: {text[:200]!r}")
    return {}


def layer2_score(jobs: list[JobPost], resume_text: str, prefs: dict) -> list[JobPost]:
    client = anthropic.Anthropic()
    for job in jobs:
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
        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            result = _parse_llm_response(message.content[0].text)
            job.llm_score = float(result.get("score", 0))
            job.llm_reason = result.get("reason", "")
        except Exception as e:
            print(f"  [error] Claude API call failed for '{job.title}': {e}")
            job.llm_score = None
    return jobs
