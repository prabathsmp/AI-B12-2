# 🔎 ReviewLens: Customer Feedback Analyzer

ReviewLens turns a week of raw customer reviews (English, Tamil or Tanglish) into tagged, prioritised insights and a weekly report a manager can read in five minutes.
Built with LangChain (LCEL + `with_structured_output`), OpenAI, Streamlit, pandas and Plotly. See [PRD.md](PRD.md) for the full spec.

```
01 Upload CSV → 02 Validate → 03 Classify (batched, auto-retry) → 04 Aggregate (pandas) → 05 Report (map→reduce) → 06 Dashboard + CSV export
```

## Quick start (Docker Desktop)

```bash
cp .env.example .env          # optional: put OPENAI_API_KEY in it
docker compose up -d --build
# open http://localhost:8501
```

Port 8501 already in use? Set `APP_PORT=8502` in `.env`, or run `APP_PORT=8502 docker compose up -d`.

**The API key is pluggable at runtime.** If `.env` holds `OPENAI_API_KEY`, the app uses it. Otherwise (or to override it) paste a key into the **sidebar**. A pasted key is held only in that browser session's memory and is never written to disk or logs. Click **Test API key** to verify it.

Then click **Use sample data** (or upload your CSV) and **Analyse**.

## Run without Docker

```bash
python -m venv .venv && .venv/Scripts/activate      # Linux/mac: source .venv/bin/activate
pip install -r requirements.txt
cd app && streamlit run streamlit_app.py
```

## Input CSV

`review_id, date, platform, rating, review_text`. Header case and spaces are tolerated. Empty rows are dropped, duplicate ids are removed, and blank ids are generated.

## What you get
| Output | Where |
|---|---|
| sentiment · category · urgency · language · summary · suggested_reply per review | **Reviews** tab, with filters (incl. **HIGH urgency only**) |
| Ready-to-post replies for urgent reviews | **Urgent queue** tab |
| Weekly report (counts, top complaints/praise, 3 action items) | **Weekly report** tab, downloadable as `.md` |
| Enriched CSV that opens in Excel (UTF-8 BOM, Tamil-safe, formula-injection-safe) | Download buttons |
| Trend arrows vs last week | Upload last week's enriched CSV in the "compare" expander |
| Reviews that failed validation after retries | **Needs review** tab, with a one-click retry |

All numbers come from pandas. The LLM only classifies, groups topic phrases into themes, and writes the wording.

## Configuration (`.env`)
| Var | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | – | Optional, can be pasted in the UI instead |
| `OPENAI_MODEL` | `gpt-4o-mini` | Default model (also selectable in the UI) |
| `MAX_CONCURRENCY` | 8 | `chain.batch(max_concurrency=…)` |
| `MAX_RETRIES` | 2 | Automatic retries before `needs_review` |
| `REQUEST_TIMEOUT` | 60 | Seconds per LLM call |
| `BUSINESS_NAME` | our restaurant | Used in prompts |
| `APP_PORT` / `BIND_ADDR` | 8501 / 0.0.0.0 | Host port mapping |

## Deploy to a VPS

```bash
# on the VPS (Docker + compose plugin installed)
git clone <your repo> reviewlens && cd reviewlens     # or scp the folder
cp .env.example .env && nano .env                    # set key; BIND_ADDR=127.0.0.1
docker compose up -d --build
```

The app has **no login**, so do not expose it directly to the internet. Put a reverse proxy with HTTPS and basic auth in front of it. Example with Caddy (`/etc/caddy/Caddyfile`):

```
reviews.example.com {
    basic_auth {
        manager <hash from: caddy hash-password>
    }
    reverse_proxy 127.0.0.1:8501
}
```

(Streamlit uses WebSockets. Caddy handles them automatically. With nginx, add `proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";`.)

Update: `git pull && docker compose up -d --build`. Logs: `docker compose logs -f`.

## Tests (offline, fake LLM, no key needed)

```bash
pip install pytest
pytest -q
```

Load test (200+ rows): `python scripts/make_load_test_csv.py 250` creates `app/sample_data/reviews_load_250.csv`. Upload it in the app.

## Project layout
```
app/
  streamlit_app.py        UI (steps 01-06)
  reviewlens/
    config.py             env settings + allowed value lists
    schemas.py            Pydantic models (ReviewAnalysis, ThemeClusters, WeeklyInsights)
    validation.py         02 validate CSV
    llm.py                model factory (the only provider-specific code)
    classifier.py         03 classify chain, batch + retry → needs_review
    aggregate.py          04 pandas stats, trends
    report.py             05 theme clustering + report chain + renderer
    export.py             06 Excel-safe CSV, load last week's export
  sample_data/reviews_week40.csv
tests/                    pipeline + headless UI tests
Dockerfile, docker-compose.yml, .env.example
```
