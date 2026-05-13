import os
import yaml
from dotenv import load_dotenv
from offerradar.fetcher import fetch_job_emails
from offerradar.parsers import parse_email
from offerradar.page_fetcher import fetch_job_details
from offerradar.repository import JobRepository
from offerradar.resume_parser import extract_resume
from offerradar.matcher import layer1_filter, layer2_score
from offerradar.digest import compose_html, send_digest

load_dotenv()

DB_PATH = "jobs.db"
RESUME_PATH = "resume.pdf"
PREFS_PATH = "preferences.yaml"


def run_pipeline():
    with open(PREFS_PATH) as f:
        prefs = yaml.safe_load(f)

    repo = JobRepository(DB_PATH)
    resume = extract_resume(RESUME_PATH)

    raw_emails = fetch_job_emails(
        host=os.environ["GMAIL_IMAP_HOST"],
        user=os.environ["GMAIL_USER"],
        password=os.environ["GMAIL_APP_PASSWORD"],
    )
    print(f"Fetched {len(raw_emails)} job alert email(s).")

    all_jobs = []
    for sender, html in raw_emails:
        all_jobs.extend(parse_email(sender, html))
    print(f"Parsed {len(all_jobs)} job listing(s).")

    new_jobs = [j for j in all_jobs if not repo.exists(j.id)]
    print(f"{len(new_jobs)} new job(s) after dedup.")

    enriched = [fetch_job_details(job) for job in new_jobs]

    for job in enriched:
        repo.save(job)

    candidates = layer1_filter(enriched, resume["keywords"], prefs)
    print(f"{len(candidates)} job(s) passed Layer 1 filter.")

    scored = layer2_score(candidates, resume_text=resume["text"], prefs=prefs)

    threshold = prefs.get("llm_score_threshold", 6.0)
    max_jobs = prefs.get("max_digest_jobs", 10)
    digest_jobs = sorted(
        [j for j in scored if (j.llm_score or 0) >= threshold],
        key=lambda j: j.llm_score or 0,
        reverse=True,
    )[:max_jobs]
    print(f"{len(digest_jobs)} job(s) qualify for digest.")

    for job in scored:
        if job.llm_score is not None:
            repo.update_scores(job.id, job.kw_score or 0, job.llm_score, job.llm_reason or "")

    html = compose_html(digest_jobs)
    if digest_jobs:
        send_digest(
            html=html,
            to_email=prefs["digest_email"],
            smtp_config={
                "host": os.environ["SMTP_HOST"],
                "port": int(os.environ["SMTP_PORT"]),
                "user": os.environ["SMTP_USER"],
                "password": os.environ["SMTP_PASSWORD"],
            },
        )
        repo.mark_sent([j.id for j in digest_jobs])
        print(f"Digest sent to {prefs['digest_email']}.")
    else:
        print("No qualifying jobs. No digest sent.")


if __name__ == "__main__":
    run_pipeline()
