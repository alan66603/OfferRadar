# OfferRadar

職缺篩選器：從 Gmail job alert 自動抓取、配對履歷、依個人偏好排序，每日寄送推薦摘要。

---

## 架構概覽

```
偏好設定 (preferences.yaml)
履歷 (resume.pdf)
        │
        ▼
┌─────────────────────────────────────────┐
│              OfferRadar Pipeline         │
│                                         │
│  1. Gmail Fetcher                       │
│     └─ IMAP 抓 LinkedIn/Glassdoor/Indeed│
│        的未讀 job alert 信              │
│                                         │
│  2. Email Parser                        │
│     └─ 各 site 專屬 parser 萃取:        │
│        職稱、公司、地點、job_url        │
│                                         │
│  3. Job Page Fetcher                    │
│     └─ 用 job_url 抓完整 job page，     │
│        萃取描述、薪資、work_type        │
│                                         │
│  4. Dedup Filter                        │
│     └─ 查 SQLite，過濾已見過的職缺      │
│                                         │
│  5. Matcher（兩層）                     │
│     Layer 1: 關鍵字 + 偏好硬過濾        │
│     Layer 2: Claude API 語意評分        │
│                                         │
│  6. Digest Composer                     │
│     └─ 組成 HTML email，寄出           │
│                                         │
│  7. SQLite (jobs.db)                    │
│     └─ 記錄所有職缺、分數、狀態        │
└─────────────────────────────────────────┘
```

六個獨立模組，每個只做一件事，可以單獨測試。

### 部署路徑

| 階段 | 執行方式 | 資料庫 | 排程 |
|------|---------|--------|------|
| MVP（本機） | Python script | SQLite | `launchd` / cron |
| 雲端 | AWS Lambda | DynamoDB | EventBridge |

資料庫存取統一走 repository 層抽象，換 backend 時上層邏輯不需修改。

---

## 資料模型

SQLite `jobs.db` 核心 schema：

```sql
CREATE TABLE jobs (
    id          TEXT PRIMARY KEY,  -- hash(url) 作為唯一 ID
    source      TEXT,              -- 'linkedin' | 'glassdoor' | 'indeed'
    title       TEXT,
    company     TEXT,
    location    TEXT,
    salary_raw  TEXT,              -- 原始薪資字串，如 "$80k–$100k"
    work_type   TEXT,              -- 'remote' | 'hybrid' | 'onsite'
    url         TEXT,
    fetched_at  TEXT,              -- ISO 8601
    kw_score    REAL,              -- Layer 1 關鍵字分數 (0–1)
    llm_score   REAL,              -- Layer 2 Claude 評分 (0–10)
    llm_reason  TEXT,              -- Claude 給的推薦理由
    status      TEXT DEFAULT 'new' -- 'new' | 'sent' | 'applied' | 'ignored'
);
```

`status` 欄位設計供未來 web dashboard 沿用。

---

## Email Parser 策略

使用 **BeautifulSoup** 解析 HTML email。每個來源有獨立 parser function，
email 階段只萃取基本欄位：

| 來源 | 解析目標 |
|------|---------|
| LinkedIn | `<a>` 超連結萃取 `job_id`，重組為公開 URL；職稱、公司、城市 |
| Glassdoor | job card `<div>` 內的職稱、公司、城市、job_url |
| Indeed | job listing `<td>` 內的職稱、公司、城市、job_url |

每個 parser 回傳統一格式的 `JobPost` dataclass（`description` 欄位此時為空）。

**LinkedIn URL 處理：** Email 中的連結為帶 token 的 `/comm/` URL，不可不登入直接使用。
Parser 用 regex 提取 `job_id`，重組成公開可爬的標準 URL：

```python
import re
match = re.search(r'/jobs/view/(\d+)', email_href)
clean_url = f"https://www.linkedin.com/jobs/view/{match.group(1)}/"
```

---

## Job Page Fetcher

Email parser 取得 `job_url` 後，抓完整 job page 補齊剩餘欄位：

| 來源 | 爬取方式 | 備註 |
|------|---------|------|
| LinkedIn | `requests` + BeautifulSoup，加 `User-Agent` header | `linkedin.com/jobs/view/{id}/` 不登入即可取得完整 JD；JS 彈窗不影響 `requests`（不執行 JS） |
| Indeed | `requests` + BeautifulSoup | 公開頁面，較寬鬆 |
| Glassdoor | `requests` 嘗試；失敗則 fallback | 部分內容需登入，fallback 給 Claude 用有限資訊評分 |

萃取欄位：`description`（全文）、`salary_raw`、`work_type`。
Fetcher 失敗時不中斷 pipeline——`description` 留空，Matcher 降權處理。

---

## Matcher 兩層邏輯

### Layer 1：關鍵字 + 偏好硬過濾

1. 用 **pdfplumber** 從 `resume.pdf` 抽出文字，解析技能關鍵字清單
2. 比對職缺描述，計算命中率 → `kw_score`
3. 套用 `preferences.yaml` 硬過濾（地點不符、work_type 不符 → 直接捨棄）
4. `kw_score >= 0.3` 才進入 Layer 2

### Layer 2：Claude API 語意評分

對 Layer 1 通過的職缺（上限 20 筆），呼叫 Claude API：

- 輸入：履歷摘要 + 職缺詳情 + 偏好設定
- 輸出：`llm_score`（0–10）+ `llm_reason`（一句話推薦理由）
- 最終排序：`llm_score` 降冪，`llm_score >= 6` 納入 digest

---

## Digest 格式

HTML email，每筆職缺包含：

```
[公司名稱] 職稱
📍 地點 ｜ 💼 work_type ｜ 💰 薪資（若有）
⭐ 評分：8.5/10
推薦理由：具備所需 Python + AWS 技能，且支援 visa sponsorship。
👉 Apply →  [連結]
```

每日最多推薦 10 筆，以 `llm_score` 排序。

---

## 偏好設定

`preferences.yaml` 範例：

```yaml
locations:
  - Melbourne
  - Sydney
  - Remote

work_types:
  - remote
  - hybrid

job_type: full-time          # 'full-time' | 'internship' | 'both'

salary_min_aud: 80000        # 年薪下限（AUD），無法解析薪資時不過濾

visa_sponsorship_required: true

keywords_must:               # 至少命中其中一個才進 Layer 2
  - Python
  - Machine Learning

keywords_nice:               # 加分關鍵字
  - AWS
  - Docker
  - FastAPI

digest_email: your@email.com
max_digest_jobs: 10
```

---

## 專案結構

```
OfferRadar/
├── resume.pdf
├── preferences.yaml
├── jobs.db                  # SQLite，git ignore
├── .env                     # Gmail IMAP 憑證、Claude API key
│
├── offerradar/
│   ├── fetcher.py           # Gmail IMAP 抓信
│   ├── parsers/
│   │   ├── linkedin.py      # Email parser：抓 title/company/location/url
│   │   ├── glassdoor.py
│   │   └── indeed.py
│   ├── page_fetcher.py      # Job page 爬蟲：補齊 description/salary/work_type
│   ├── matcher.py           # 兩層配對邏輯
│   ├── digest.py            # HTML email 組裝 + 寄送
│   ├── repository.py        # SQLite CRUD 抽象層
│   └── models.py            # JobPost dataclass
│
├── main.py                  # Pipeline 進入點
├── requirements.txt
└── README.md
```

---

## 快速開始

```bash
pip install -r requirements.txt
cp .env.example .env         # 填入 Gmail App Password 和 Claude API key
python main.py
```
