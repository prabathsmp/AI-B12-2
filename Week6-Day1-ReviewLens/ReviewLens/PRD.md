# ReviewLens — Product Requirements Document

| | |
|---|---|
| **Product** | ReviewLens: Customer Feedback Analyzer |
| **Track** | Gen AI · LangChain (Intermediate) |
| **Interface** | Streamlit web app, packaged with Docker Compose |
| **LLM** | OpenAI (default `gpt-4o-mini`), key supplied at runtime |
| **Status** | v1.0, built. Open questions resolved |
| **Last updated** | 2026-11-21 |

---

## 1. Problem

A restaurant chain or online store gets 200–500 reviews a week from Google, Zomato, Swiggy and Amazon, in English, Tamil and Tanglish. A manager reads them by hand. Urgent complaints (food poisoning, wrong order, rude staff) go unnoticed for days, and nobody can say with numbers what customers complain about most.

## 2. Goal

Turn one week's raw reviews into tagged, prioritised insights and a weekly report that a manager can act on in **five minutes**.

### Success metrics (from the "Done" checklist)

| # | Criterion | How we meet it |
|---|---|---|
| S1 | Processes a 200+ row CSV without crashing or timing out | Chunked `chain.batch()` with `max_concurrency`, per-request timeout, SDK retries for rate limits, a progress bar, and per-row error isolation (`return_exceptions=True`) |
| S2 | Every review has all 6 fields, and every value is from the allowed list | Pydantic model with `Literal` enums plus OpenAI strict JSON-schema output. Invalid rows are retried automatically, then marked `needs_review` |
| S3 | Tamil and Tanglish reviews get a correct English summary | The prompt includes language rules and few-shot examples. `language` is detected per review |
| S4 | Report numbers exactly match the table | Every count and percentage is computed in **pandas**. The LLM only writes labels and action items and never produces a number shown as a statistic |
| S5 | HIGH urgency filter works and the CSV opens correctly in Excel | Dashboard filter. CSV is exported as UTF-8 with BOM (`utf-8-sig`) so Tamil text renders in Excel |
| S6 | API key loaded from `.env`, never hard-coded | `OPENAI_API_KEY` from `.env` / env vars, can be overridden in the sidebar for the session (kept in memory, never written to disk) |

## 3. Users

| Persona | Need |
|---|---|
| Operations manager | Weekly report, top issues, action items |
| Customer support team | HIGH-urgency queue with ready-to-post replies, exported to Excel |
| Business owner | Overall sentiment split and trend versus last week |

## 4. Scope

### In scope (v1)
1. CSV upload (`review_id, date, platform, rating, review_text`)
2. Validation: required columns, drop empty rows, type checks, de-duplicate `review_id`
3. Per-review classification chain (map) with structured output
4. Automatic retry of invalid outputs, then `needs_review`
5. Aggregation in pandas
6. Weekly insights report chain (reduce)
7. Dashboard: KPIs, sentiment split, category chart, urgency/platform/category filters, HIGH-only toggle
8. Export: enriched CSV (Excel-safe) and the weekly report (Markdown)
9. Runtime-pluggable OpenAI API key and model
10. Docker Compose deployment (local Docker Desktop, then VPS)

### Stretch goals
| Goal | v1 status |
|---|---|
| Compare with last week (trend arrows) | **Included**: upload last week's enriched CSV and see deltas |
| Replies in the same language as the review | **Included**: sidebar toggle |
| Email the report every Monday | **Not required** (product owner decision) |

### Out of scope
Scraping reviews from platforms, posting replies back to platforms, user accounts or multi-tenant storage, persistent database.

## 5. Workflow

```
01 Upload CSV ─▶ 02 Validate ─▶ 03 Classify (map, batched) ─▶ 04 Aggregate (pandas)
                                     │ retry invalid ▶ needs_review
                                                               ─▶ 05 Report (reduce) ─▶ 06 Show + Export
```

| Step | Behaviour |
|---|---|
| **01 Upload** | `st.file_uploader` for CSV. A sample file is offered for a demo run |
| **02 Validate** | Column names are normalised (trimmed, case-insensitive). Reject if a required column is missing. Drop rows with empty `review_text`. Coerce `rating` to 1–5 (invalid becomes blank), parse `date`, drop duplicate `review_id` (keep first), generate an id if it is blank. Show a validation summary (rows read / kept / dropped with reasons) |
| **03 Classify** | `ChatPromptTemplate | llm.with_structured_output(ReviewAnalysis)`. Runs via `chain.batch(inputs, config={"max_concurrency": N}, return_exceptions=True)` in chunks so the UI can show progress |
| **03a Retry** | A row that raised a parse or validation error, or returned an invalid value, is re-sent up to `MAX_RETRIES` (default 2). If it still fails, `status = needs_review`, the enum fields are left blank, and the error is recorded |
| **04 Aggregate** | pandas: counts and percentages by sentiment, category, urgency, platform. Date range. Urgent count |
| **05 Report** | Map then reduce: (a) a theme chain clusters the per-review `topic` phrases into a few themes. (b) pandas counts reviews per theme. (c) the report chain gets the pre-computed facts and representative summaries and writes theme labels, context lines and exactly 3 action items. Numbers in the report are rendered from pandas |
| **06 Show + Export** | Dashboard tabs: Overview, Reviews (filterable table), Urgent queue, Weekly report. Download the enriched CSV and the report |

## 6. Data contract

### Input CSV
| Column | Type | Rules |
|---|---|---|
| review_id | string | Unique. Generated if blank |
| date | date (YYYY-MM-DD) | Unparseable values are kept as text and flagged |
| platform | string | Free text (Google, Zomato, Swiggy, Amazon, …) |
| rating | int 1–5 | Optional, used as a hint |
| review_text | string | Required, non-empty |

### Per-review output (6 required fields + helpers)
| Field | Allowed values |
|---|---|
| sentiment | `positive`, `neutral`, `negative` |
| category | `food_quality`, `delivery`, `price`, `staff`, `packaging`, `app` |
| urgency | `low`, `medium`, `high` |
| language | `English`, `Tamil`, `Tanglish`, `Other` |
| summary | One English sentence, at most 30 words |
| suggested_reply | Polite, ready to post, 1–3 sentences, no fabricated promises (no specific refund amounts) |
| topic *(helper)* | 2–4 word English key phrase, e.g. "late delivery", "biryani taste", used for theme counts |
| status *(system)* | `ok` or `needs_review` |
| error *(system)* | Last error message when `needs_review` |

### Urgency rules
- **high**: reply today. Covers health or food safety (food poisoning, foreign object, stale food), wrong or missing order, refund or payment dispute, abusive or rude staff, legal threats, and severe delivery failure (very late and inedible).
- **medium**: a clear complaint that needs follow-up within a few days (late, cold, overcharged, small portion, app glitch).
- **low**: positive, neutral, or a minor suggestion.

### Weekly report (Output B)
Header with date range and total. Sentiment percentages. Top 3 complaint themes with counts and their dominant platform/category. Top praise themes with mention counts. Urgent count. 3 action items. Optional trend versus last week.

## 7. Functional requirements

| ID | Requirement |
|---|---|
| FR-1 | The user can enter an OpenAI API key in the sidebar. If `.env` holds one, it is used by default and the sidebar can override it for the session |
| FR-2 | The user can pick the model (default from `OPENAI_MODEL`), batch concurrency and reply language mode |
| FR-3 | The app validates the upload and reports dropped rows with reasons |
| FR-4 | Analysis shows a progress bar and an ETA, and can handle 500 rows |
| FR-5 | Results are cached in the session, so changing filters does not re-call the LLM |
| FR-6 | The HIGH-urgency toggle shows only `urgency == high` |
| FR-7 | Enriched CSV download: original columns + 6 fields + topic + status |
| FR-8 | Report download as Markdown |
| FR-9 | Optional upload of last week's enriched CSV to show trend arrows |
| FR-10 | `needs_review` rows are listed separately and can be retried with one click |

## 8. Non-functional requirements
- **Security**: no hard-coded keys. `.env` is git-ignored and docker-ignored. A key typed in the sidebar lives only in session memory.
- **Performance**: about 250 reviews in under 2 minutes at concurrency 8 with `gpt-4o-mini`.
- **Resilience**: one failed review never fails the batch. Rate-limit errors (429) are retried with backoff by the SDK.
- **Portability**: the LLM is built in one factory function, so a different provider can be swapped in without changing the chains.
- **Deployability**: one `docker compose up -d --build`. Healthcheck, restart policy, no root user in the container.

## 9. Tech stack
| Part | Choice |
|---|---|
| Chains | LangChain `ChatPromptTemplate`, LCEL (`|`) |
| Structured output | Pydantic v2 + `with_structured_output(method="json_schema")` |
| Batching | `chain.batch()` with `max_concurrency` |
| LLM | OpenAI via `langchain-openai` |
| UI | Streamlit + pandas + Plotly |
| Packaging | Docker (python:3.12-slim) + Docker Compose |

## 10. Decisions (confirmed by product owner, 2026-11-21)
| # | Decision |
|---|---|
| D1 | One CSV is one week. The report date range comes from the min/max `date` in the file |
| D2 | Only the 6 listed categories are allowed (no `other`). A review that touches several categories gets its **primary** one |
| D3 | Rows that fail after retries are marked `needs_review` with blank enum fields, not guessed, and are excluded from percentages |
| D4 | No order-time column. Time-of-day insights appear only if the review text mentions a time |
| D5 | No login in the app. On a VPS, use a reverse proxy with HTTPS (basic auth optional, see README) |
| D6 | Email automation is not required |

## 11. Milestones
| Day | Deliverable |
|---|---|
| 1 | PRD, validation, classification chain with retry, sample data |
| 2 | Aggregation, report chain, dashboard, exports |
| 3 | Trend comparison, Docker Compose, tests, README, 250-row load test |
