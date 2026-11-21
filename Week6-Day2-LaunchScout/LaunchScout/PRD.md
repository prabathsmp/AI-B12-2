# PRD — LaunchScout: Competitor Research Crew

| Item | Detail |
|---|---|
| Track | Track 2 — AI Agents (CrewAI) |
| Level | Intermediate |
| Version | 1.0 |
| Date | 2026-11-21 |
| Source | `Requirement.docx` |

---

## 1. Problem statement

A founder about to launch a new business (e.g. *healthy millet meal boxes in Coimbatore*) needs to know, before spending money:

- Who the competitors are
- What they charge
- What their customers complain about
- Where the gap in the market is

Today this takes a marketing intern **2–3 days** of manual searching and copying into Excel. LaunchScout reduces this to **a few minutes** with a crew of four cooperating AI agents that produce a sourced, founder-friendly report.

## 2. Target users

| Persona | Need |
|---|---|
| Founders | Fast validation of an idea and a price point before launch |
| Marketing teams | Competitive landscape and positioning for a new product line |
| Business consultants | Quick first-pass market scan for a client |
| Students | Evidence-backed competitor slide for a pitch deck |

## 3. Goals and non-goals

**Goals**
1. Find **3–5 real competitors** with price, offers and sales channels — each with at least one source link.
2. Surface customer **likes and complaints** per competitor.
3. Produce a **comparison matrix**, the **market gap**, and a **recommended positioning with price**.
4. Deliver a **6-section report** viewable in the app and downloadable as **Markdown and PDF**, also saved to `report.md`.
5. Show **live progress**: which agent is working and what it found.
6. Work for **any idea and city without code changes**.
7. **Pluggable LLM key** — the OpenAI API key (and model / base URL) is supplied via environment or the UI, never hard-coded.

**Non-goals (v1)**
- User accounts, multi-tenant persistence, or report history database.
- Paid data sources beyond web search (Serper) and public pages.
- Guaranteeing price accuracy beyond what the cited pages state.

## 4. Solution overview

A CrewAI `Crew` of four agents executed with `Process.sequential` (stretch: `Process.hierarchical` toggle). Each task receives the previous tasks' output as `context`, like a real team passing work along.

```
 ┌──────────┐   ┌────────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
 │01 Idea   │──▶│02 Research │──▶│03 Reviews│──▶│04 Strategy│─▶│05 Write  │──▶│06 Deliver│
 │ input    │   │ Researcher │   │ Analyst  │   │ Strategist│  │ Writer   │   │ view/dl  │
 └──────────┘   └────────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
```

### 4.1 Agents

| Agent | Role & goal | Tools |
|---|---|---|
| Market Researcher | Find 3–5 real competitors with prices, offers and sales channels | Web search (Serper; DuckDuckGo fallback), website scraper |
| Review Analyst | Find what customers like and complain about for each competitor | Web search, website scraper |
| Strategy Analyst | Build comparison matrix, find the market gap, suggest price & positioning | None (reasons over previous agents' work) |
| Report Writer | Write a clean, founder-friendly report with sources | File writer (saves `report.md`) |

Each agent has a distinct `role`, `goal`, `backstory`, tool set and the shared pluggable `llm`.

### 4.2 Tasks

| Task | Agent | Context | Expected output (checkable) |
|---|---|---|---|
| `research_task` | Market Researcher | — | Markdown list of 3–5 competitors; each with name, website, price per unit (with currency), offers, channels, strength, weakness, ≥1 source URL |
| `review_task` | Review Analyst | research | Per competitor: 2–4 likes, 2–4 complaints, each with source URL; plus cross-competitor common complaints |
| `strategy_task` | Strategy Analyst | research, review | Comparison matrix table; one-paragraph market gap; one-line positioning with price; pricing rationale |
| `report_task` | Report Writer | research, review, strategy | Full Markdown report with exactly the 6 sections below, saved to `report.md` |

### 4.3 Report structure (6 sections)

| # | Section | Produced by | Tells the founder |
|---|---|---|---|
| 1 | Key Competitors (table) | Market Researcher | Who sells, at what price, on which platform |
| 2 | What Customers Complain About | Review Analyst | Pain points they can solve better |
| 3 | Market Gap | Strategy Analyst | The one opportunity nobody serves well |
| 4 | Recommended Positioning | Strategy Analyst | A clear one-line offer with a price |
| 5 | 30-Day Launch Plan | Report Writer | Practical first steps, week by week |
| 6 | Sources | All agents | Numbered links so every number is verifiable |

Every price or claim carries an inline citation `[n]` that maps to a URL in **Sources**.

## 5. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Input form: business idea (required), city (required), target customer (required), known competitors (optional) | Must |
| FR-2 | Quick-fill sample ideas (e.g. millet meal boxes, Coimbatore) | Should |
| FR-3 | Run the four-agent crew sequentially with task context chaining | Must |
| FR-4 | Live progress panel: per-agent status (waiting / working / done) and a streaming activity log (tool calls, findings) | Must |
| FR-5 | Render final report in-app (Markdown) | Must |
| FR-6 | Download report as `.md` and `.pdf` | Must |
| FR-7 | Save `report.md` to a per-run output folder (mounted volume in Docker) | Must |
| FR-8 | Show each agent's intermediate output in the app | Should |
| FR-9 | LLM settings pluggable: API key, model name, optional OpenAI-compatible base URL — via `.env` or sidebar | Must |
| FR-10 | Serper key optional; fall back to DuckDuckGo search when absent | Should |
| FR-11 | Process toggle: sequential (default) / hierarchical (stretch) | Could |
| FR-12 | Clear error messages for missing key, LLM/tool failures | Must |

## 6. Non-functional requirements

| Area | Requirement |
|---|---|
| Runtime | Single `docker compose up` on Docker Desktop; app at `http://localhost:8501` |
| Performance | Typical run completes in 2–6 minutes depending on model & search |
| Security | Keys only from env / session; never logged, never written to disk; `.env` excluded from image |
| Portability | Python 3.12 slim image; no OS-specific code |
| UX | Modern, visually rich dark theme (aurora gradient, glass cards, animated agent status), responsive layout |
| Reliability | Agent `max_iter` caps; tool errors surface in log and don't crash the UI |
| Configurability | No code change needed for new idea / city / model |

## 7. Tech stack

| Part | Use |
|---|---|
| CrewAI `Agent` | role, goal, backstory, tools, llm, per-agent step callback |
| CrewAI `Task` | description, expected_output, context, agent, output_file |
| `Crew` + `Process` | `Process.sequential` (stretch: `hierarchical` with manager LLM) |
| Tools | `SerperDevTool`, `ScrapeWebsiteTool`, `FileWriterTool`, custom DuckDuckGo tool |
| LLM | `crewai.LLM` — OpenAI by default, any OpenAI-compatible endpoint via base URL |
| Output | `output_file` → `report.md`; Markdown → HTML → PDF (`xhtml2pdf`) |
| UI | Streamlit with custom CSS theme and live step log |
| Packaging | Dockerfile + docker-compose, `.env` for secrets |

## 8. Configuration

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes (or enter in UI) | — | LLM key |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Model name |
| `OPENAI_BASE_URL` | No | — | OpenAI-compatible endpoint (Azure/OpenRouter/local) |
| `SERPER_API_KEY` | No | — | Google search via Serper; DuckDuckGo used if absent |

## 9. Acceptance criteria (Done checklist)

- [ ] Four agents with clearly different roles, goals and backstories.
- [ ] Every task has an `expected_output` describing the exact format.
- [ ] At least 3 competitors found, each with a price and at least one source link.
- [ ] Report contains all 6 sections and is saved to a file.
- [ ] The app shows which agent is working while the crew runs.
- [ ] Works for a different idea and city without changing any code.
- [ ] Runs in local Docker Desktop with a pluggable OpenAI key.

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Hallucinated competitors / prices | Prompts require URLs for every claim; "Not found" allowed instead of guessing; sources section |
| Sites block scraping | Agents fall back to search snippets; scraper errors are non-fatal |
| No Serper key | DuckDuckGo fallback tool |
| Long runs / cost | `max_iter` limits; default to a small, cheap model; model configurable |
| Rate limits | `max_rpm` on crew; clear error surfaced in UI |

## 11. Future scope

- Hierarchical process as default with a manager agent that re-tasks weak sections.
- Export to PPTX for pitch decks; report history.
- Google Maps / review-platform specific tools.
