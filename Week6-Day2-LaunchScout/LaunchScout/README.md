# 🛰️ LaunchScout — Competitor Research Crew

A **CrewAI** team of four AI agents that researches the market for a new business idea and delivers a
sourced competitor report with prices, customer complaints, the market gap, a priced positioning and a
30-day launch plan. See [PRD.md](PRD.md) for the full product requirements.

| Agent | Job | Tools |
|---|---|---|
| 🔎 Market Researcher | 3–5 real competitors with prices, offers, channels | Web search (Serper or DuckDuckGo), website scraper |
| 💬 Review Analyst | What customers like / complain about | Web search, website scraper |
| 🧭 Strategy Analyst | Comparison matrix, market gap, price & positioning | — (reasons over teammates' work) |
| ✍️ Report Writer | Founder-friendly 6-section report with sources | File writer (`report.md`) |

Tasks run with `Process.sequential`, and each task gets the earlier tasks' output as `context`. A hierarchical mode is available as a toggle in the sidebar.

---

## Quick start (Docker Desktop)

```bash
# 1. Configure keys (the OpenAI key is pluggable: .env OR paste it in the app sidebar)
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
#    edit .env -> OPENAI_API_KEY=sk-...   (SERPER_API_KEY optional)

# 2. Build & run
docker compose up --build -d

# 3. Open the app
#    http://localhost:8501
```

Reports are saved to `./outputs/run_<timestamp>/report.md` on your machine (mounted volume).

Stop it with `docker compose down`.

### Pluggable LLM

| Setting | `.env` variable | Sidebar field | Default |
|---|---|---|---|
| API key | `OPENAI_API_KEY` | OpenAI API key | — |
| Model | `OPENAI_MODEL` | Model | `gpt-4o-mini` |
| OpenAI-compatible endpoint | `OPENAI_BASE_URL` | Base URL | OpenAI |
| Google search via Serper | `SERPER_API_KEY` | Serper API key | DuckDuckGo fallback |

Values typed in the sidebar override `.env` for that browser session only. They are never written to disk.

Any OpenAI-compatible server works through the base URL, e.g. Azure OpenAI, OpenRouter, or a local
**Ollama** (`Base URL = http://host.docker.internal:11434/v1`, `Model = qwen2.5:latest`, key = any text).

## Run without Docker

```bash
python -m venv .venv && .venv/Scripts/activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Project layout

```
app.py              Streamlit UI (form, live agent board, activity log, report + downloads)
scout/config.py     Pluggable settings -> crewai.LLM
scout/crew.py       Agents, tasks (expected_output), crew, live event routing
scout/tools.py      Serper / DuckDuckGo search, trimmed website scraper, file writer
scout/pdf.py        Markdown -> styled PDF
scout/theme.py      Custom aurora/glass theme + HTML components
Dockerfile, docker-compose.yml, .env.example
PRD.md              Product requirements document
```

## Done checklist

- [x] Four agents with distinct roles, goals and backstories
- [x] Every task has an `expected_output` describing the exact format
- [x] 3+ competitors, each with price and source link (prompts enforce URLs; "Not found" instead of guessing)
- [x] Report with all 6 sections, saved to `report.md` (file writer tool + `output_file`)
- [x] Live view of which agent is working and what tools it is calling
- [x] Works for any idea and city with no code change (inputs are interpolated at kickoff)

> Result quality depends on the model and the search provider. `gpt-4o-mini` with Serper gives the best
> price coverage. Always check numbers against the linked sources.
