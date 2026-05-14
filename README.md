# OfferRadar

A personal job alert pipeline that reads Gmail job alert emails (LinkedIn, Glassdoor, Indeed), matches them against your resume, applies your preferences, and sends a scored HTML digest via email.

---

## Architecture

```
preferences.yaml + resume.pdf
          │
          ▼
┌─────────────────────────────────────────┐
│           OfferRadar Pipeline           │
│                                         │
│  1. Gmail Fetcher                       │
│     └─ IMAP search by sender domain     │
│        for the past N days              │
│                                         │
│  2. Email Parser                        │
│     └─ Per-source parsers extract:      │
│        title, company, location, url    │
│                                         │
│  3. Job Page Fetcher                    │
│     └─ Scrapes full job page for        │
│        description, salary, work_type   │
│                                         │
│  4. Dedup Filter                        │
│     └─ Checks SQLite, skips seen jobs   │
│                                         │
│  5. Matcher (two layers)                │
│     Layer 1: keyword + prefs hard filter│
│     Layer 2: Claude API semantic score  │
│                                         │
│  6. Digest Composer                     │
│     └─ Builds HTML email and sends it   │
│                                         │
│  7. SQLite (jobs.db)                    │
│     └─ Stores all jobs, scores, status  │
└─────────────────────────────────────────┘
```

Each module has one responsibility and can be tested independently.

### Deployment path

| Stage | Runtime | Database | Scheduler |
|-------|---------|----------|-----------|
| MVP (local) | Python script | SQLite | `launchd` / cron |
| Cloud | AWS Lambda | DynamoDB | EventBridge |

All database access goes through a repository abstraction — swapping the backend requires no changes to pipeline logic.

---

## Data Model

SQLite `jobs.db` schema:

```sql
CREATE TABLE jobs (
    id          TEXT PRIMARY KEY,  -- sha256(url)[:16]
    source      TEXT,              -- 'linkedin' | 'glassdoor' | 'indeed'
    title       TEXT,
    company     TEXT,
    location    TEXT,
    salary_raw  TEXT,              -- raw string e.g. "$80k–$100k"
    work_type   TEXT,              -- 'remote' | 'hybrid' | 'onsite'
    url         TEXT,
    fetched_at  TEXT,              -- ISO 8601 UTC
    kw_score    REAL,              -- Layer 1 keyword score (0–1)
    llm_score   REAL,              -- Layer 2 Claude score (0–10)
    llm_reason  TEXT,              -- one-sentence reason from Claude
    status      TEXT DEFAULT 'new' -- 'new' | 'sent' | 'applied' | 'ignored'
);
```

The `status` field is reserved for a future web dashboard.

---

## Email Parsers

Each source has a dedicated parser built with **BeautifulSoup**. The email stage extracts only basic fields; the full description is fetched separately in the next stage.

| Source | Approach |
|--------|----------|
| LinkedIn | Extracts `job_id` from `/comm/` token URLs via regex, reconstructs public URL; parses title, company, city |
| Glassdoor | Finds `jobListingId` in `partner/jobListing.htm` links, reconstructs canonical URL; extracts title and company from styled spans |
| Indeed | Parses `<td>` table rows for title, company, city, and job URL |

**LinkedIn URL handling:** Email links are `/comm/` URLs with tracking tokens that require login. The parser extracts the numeric `job_id` and builds a public URL:

```python
match = re.search(r'/jobs/view/(\d+)', email_href)
clean_url = f"https://www.linkedin.com/jobs/view/{match.group(1)}/"
```

---

## Job Page Fetcher

After parsing emails, the fetcher scrapes each job page to fill in description, salary, and work type.

| Source | Method | Notes |
|--------|--------|-------|
| LinkedIn | `requests` + BeautifulSoup with `User-Agent` header | Public job pages work without login; JS popups don't affect `requests` |
| Indeed | `requests` + BeautifulSoup | Lenient public pages |
| Glassdoor | `requests` with fallback | Some content requires login; Claude scores with limited info on fallback |

If a fetch fails, `description` is left empty and the job is scored with lower weight — the pipeline never aborts.

---

## Matcher

### Layer 1 — Keyword + preference hard filter

Filters out jobs that don't meet any of these conditions:

- Location not in `locations`
- Work type not in `work_types`
- Description mentions `N+ years` experience where `N >= max_years_experience`
- Description or title contains any `keywords_exclude` term
- Keyword hit rate below `kw_score_threshold`

### Layer 2 — Claude semantic scoring

Calls `claude-haiku-4-5` for each Layer 1 candidate:

- **Input:** resume excerpt + job details + preferences
- **Output:** `llm_score` (0–10) + `llm_reason` (one sentence)
- Jobs with `llm_score >= llm_score_threshold` are included in the digest, sorted by score descending

---

## Digest Format

Each job card in the HTML email:

```
[Company] — Job Title
📍 Location  |  💼 work_type  |  💰 Salary (if available)
⭐ Score: 8.5/10
Reason: Strong match on Python and AWS; no visa sponsorship required.
Apply →  [link]
```

Up to `max_digest_jobs` jobs per digest, sorted by `llm_score`.

---

## Configuration

Edit `preferences.yaml` to control filtering:

```yaml
locations:
  - Taipei
  - Melbourne
  - Remote

work_types:
  - remote
  - hybrid
  - onsite

job_type: internship          # 'full-time' | 'internship' | 'both'

max_years_experience: 2       # exclude jobs requiring 2+ years experience; null = off

keywords_must:                # job must match at least one
  - Python
  - Cloud

keywords_nice:                # boost Layer 1 score if present
  - AWS
  - Docker
  - Kubernetes

keywords_exclude:             # immediately discard if any match
  - Firmware
  - Security Clearance

days_back: 3                  # how many days of emails to fetch

digest_email: your@email.com
max_digest_jobs: 10
llm_score_threshold: 6.0
kw_score_threshold: 0.2
```

---

## Project Structure

```
OfferRadar/
├── resume.pdf               # your resume (git-ignored)
├── preferences.yaml         # filtering config
├── jobs.db                  # SQLite database (git-ignored)
├── .env                     # credentials (git-ignored)
│
├── offerradar/
│   ├── fetcher.py           # Gmail IMAP fetcher
│   ├── parsers/
│   │   ├── linkedin.py
│   │   ├── glassdoor.py
│   │   └── indeed.py
│   ├── page_fetcher.py      # job page scraper
│   ├── matcher.py           # two-layer matching logic
│   ├── digest.py            # HTML email composer + SMTP sender
│   ├── repository.py        # SQLite CRUD abstraction
│   └── models.py            # JobPost dataclass
│
├── main.py                  # pipeline entry point
├── tests/
├── requirements.txt
└── README.md
```

---

## Quick Start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp /path/to/your/resume.pdf resume.pdf
python main.py
```

### .env

```
GMAIL_IMAP_HOST=imap.gmail.com
GMAIL_USER=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx

ANTHROPIC_API_KEY=sk-ant-...
```

> Gmail App Password: Google Account → Security → 2-Step Verification → App passwords
