# OfferRadar

A personal job alert pipeline that reads Gmail job alert emails (LinkedIn, Glassdoor, Indeed), matches them against your resume, scores them with Claude, and pushes results to Telegram.

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
│        (UNSEEN + SINCE N days)          │
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
│  6. Telegram Notifier                   │
│     └─ Sends one message per job        │
│                                         │
│  7. SQLite (jobs.db)                    │
│     └─ Stores all jobs, scores, status  │
└─────────────────────────────────────────┘
```

Each module has one responsibility and can be tested independently.

### Deployment

| Stage | Runtime | Database | Scheduler |
|-------|---------|----------|-----------|
| Local | Python script | SQLite (local) | manual / cron |
| Cloud | AWS Lambda | SQLite on S3 | EventBridge (every 4 hours on weekdays) |

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

---

## Email Parsers

Each source has a dedicated parser built with **BeautifulSoup**. The email stage extracts only basic fields; the full description is fetched separately in the next stage.

| Source | Approach |
|--------|----------|
| LinkedIn | Extracts `job_id` from `/comm/` token URLs via regex, reconstructs public URL; parses title, company, city |
| Glassdoor | Finds `jobListingId` in `partner/jobListing.htm` links, reconstructs canonical URL; extracts title and company from styled spans |
| Indeed | Parses `<td>` table rows for title, company, city, and job URL |

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
- Jobs with `llm_score >= llm_score_threshold` are sent to Telegram, sorted by score descending

---

## Telegram Message Format

```
Company — Job Title
📍 Location  |  💼 work_type
⭐ Score: 8.5/10
Strong match on Python and AWS.
Apply →
```

Up to `max_digest_jobs` jobs per run, sorted by `llm_score`.

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

days_back: 1                  # how many days of emails to fetch (also limits Lambda UNSEEN scan)

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
├── lambda_handler.py        # AWS Lambda entry point
│
├── offerradar/
│   ├── fetcher.py           # Gmail IMAP fetcher
│   ├── parsers/
│   │   ├── linkedin.py
│   │   ├── glassdoor.py
│   │   └── indeed.py
│   ├── page_fetcher.py      # job page scraper
│   ├── matcher.py           # two-layer matching logic
│   ├── notifier.py          # Telegram sender
│   ├── db_sync.py           # S3 download/upload for jobs.db
│   ├── repository.py        # SQLite CRUD abstraction
│   └── models.py            # JobPost dataclass
│
├── deploy/
│   ├── package.sh           # builds Lambda deployment zip
│   └── setup_aws.sh         # one-time AWS resource creation
│
├── main.py                  # pipeline entry point
├── tests/
├── requirements.txt
└── README.md
```

---

## Local Quick Start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp /path/to/your/resume.pdf resume.pdf
# edit .env with your credentials
python main.py
```

---

## Cloud Deployment (AWS Lambda)

### Prerequisites

- AWS CLI installed and configured (`aws configure`)
- Telegram bot created via `@BotFather` — copy the token
- Send any message to your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` to find your `chat.id`

### .env

```
GMAIL_IMAP_HOST=imap.gmail.com
GMAIL_USER=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

ANTHROPIC_API_KEY=sk-ant-...

TELEGRAM_BOT_TOKEN=123456789:AAxxxxxx
TELEGRAM_CHAT_ID=987654321

S3_BUCKET=offerradar-state
```

> Gmail App Password: Google Account → Security → 2-Step Verification → App passwords

### First deploy

```bash
# 1. Build the Lambda zip (downloads Linux x86_64 wheels)
source venv/bin/activate
./deploy/package.sh

# 2. Create all AWS resources (S3, IAM role, Lambda, EventBridge)
export $(grep -v '^#' .env | xargs)
./deploy/setup_aws.sh
```

This creates:
- S3 bucket for `jobs.db` and `resume.pdf` persistence
- IAM role with Lambda execution + S3 read/write/list permissions
- Lambda function (Python 3.12, 10 min timeout, 512 MB)
- EventBridge rule triggering every 4 hours on weekdays

### Test invoke

```bash
aws lambda invoke \
    --function-name offerradar \
    --log-type Tail \
    --query 'LogResult' \
    --output text \
    /tmp/response.json | base64 -d
```

### Redeploy after code or config changes

```bash
./deploy/package.sh
aws lambda update-function-code \
    --function-name offerradar \
    --zip-file fileb://offerradar_lambda.zip
```

### Update environment variables only

```bash
# Write vars to a JSON file first to handle special characters (e.g. spaces in App Password)
aws lambda update-function-configuration \
    --function-name offerradar \
    --environment file:///path/to/env.json
```

### Reset the database

```bash
# Delete jobs.db from S3 (Lambda will start fresh on next run)
aws s3 rm s3://offerradar-state/jobs.db

# Or locally:
rm jobs.db
```
