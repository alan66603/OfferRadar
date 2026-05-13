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

    print("Parsing resume...")
    resume = extract_resume(RESUME_PATH)
    print(f"  Keywords extracted: {', '.join(resume['keywords'][:10])}")

    print("\nConnecting to Gmail IMAP...")
    raw_emails = fetch_job_emails(
        host=os.environ["GMAIL_IMAP_HOST"],
        user=os.environ["GMAIL_USER"],
        password=os.environ["GMAIL_APP_PASSWORD"],
    )
    print(f"  Fetched {len(raw_emails)} job alert email(s) from the past 7 days.")

    print("\nParsing emails...")
    all_jobs = []
    for sender, html in raw_emails:
        jobs = parse_email(sender, html)
        all_jobs.extend(jobs)
        print(f"  {sender[:50]}: {len(jobs)} listing(s)")
    print(f"  Total parsed: {len(all_jobs)} job listing(s).")

    new_jobs = [j for j in all_jobs if not repo.exists(j.id)]
    print(f"  {len(new_jobs)} new (not seen before), {len(all_jobs) - len(new_jobs)} already in DB.")

    if not new_jobs:
        print("\nNo new jobs to process. Exiting.")
        return

    print(f"\nFetching job page details for {len(new_jobs)} job(s)...")
    enriched = []
    for i, job in enumerate(new_jobs, 1):
        print(f"  [{i}/{len(new_jobs)}] {job.company} — {job.title}")
        enriched.append(fetch_job_details(job))

    for job in enriched:
        repo.save(job)
    print(f"  Saved {len(enriched)} job(s) to DB.")

    print("\nLayer 1: keyword filter...")
    candidates = layer1_filter(enriched, resume["keywords"], prefs)
    print(f"  {len(candidates)}/{len(enriched)} job(s) passed.")

    if not candidates:
        print("\nNo candidates after Layer 1. No digest sent.")
        return

    print(f"\nLayer 2: Claude scoring {len(candidates)} job(s)...")
    scored = layer2_score(candidates, resume_text=resume["text"], prefs=prefs)
    for job in scored:
        score = f"{job.llm_score:.1f}" if job.llm_score is not None else "?"
        print(f"  {job.company} — {job.title}: {score}/10")

    threshold = prefs.get("llm_score_threshold", 6.0)
    max_jobs = prefs.get("max_digest_jobs", 10)
    digest_jobs = sorted(
        [j for j in scored if (j.llm_score or 0) >= threshold],
        key=lambda j: j.llm_score or 0,
        reverse=True,
    )[:max_jobs]
    print(f"\n  {len(digest_jobs)} job(s) scored >= {threshold} (digest threshold).")

    for job in scored:
        if job.llm_score is not None:
            repo.update_scores(job.id, job.kw_score or 0, job.llm_score, job.llm_reason or "")

    if digest_jobs:
        print(f"\nSending digest to {prefs['digest_email']}...")
        html = compose_html(digest_jobs)
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
        print("  Done.")
    else:
        print("\nNo qualifying jobs. No digest sent.")


if __name__ == "__main__":
    run_pipeline()
