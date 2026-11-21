# 🛰️ DataPilot — Self-Correcting Data Analyst

Ask a business question in plain English. A team of **Microsoft AutoGen** agents plans the analysis, writes
Python, runs it in a sandbox, **fixes its own errors**, gets reviewed, and returns a plain-English answer with
charts and a re-runnable `analysis.py`.

> Numbers come from code, not from the LLM.

---

## Highlights

- **4 agents + you**: Planner · Coder · Executor (sandbox) · Reviewer · User Proxy (human approval)
- **Self-correction loop**: Executor error or Reviewer feedback → back to the Coder automatically
- **Safe & bounded**: stops on `APPROVED` or after 12 messages; code runs only in the container's session folder
- **Live agent conversation** with colour-coded badges (CODE / FIX / ERROR / OK / FEEDBACK / APPROVED) and a pipeline stepper
- **Outputs**: answer card, PNG charts (titled, labelled, with units), `analysis.py`, **PDF report**, zip bundle
- **Re-run & verify**: proves the saved script reproduces exactly the same numbers
- **Follow-up questions** continue the same agent session (AutoGen team state is saved/loaded)
- **Bring your own OpenAI key** in the UI — kept in session memory only
- CSV and **multi-sheet Excel**; one-click sample dataset (`sales_2026.csv`, 12,480 rows)
- Choose **SelectorGroupChat** (smart routing, default) or **RoundRobinGroupChat**

## Quick start — Docker Desktop (recommended)

```bash
docker compose up --build -d
```
Open **http://localhost:8503** (override with `DATAPILOT_PORT=xxxx docker compose up -d`), then:
1. Paste your **OpenAI API key** in the sidebar (optionally click *Test key*) and pick a model.
2. Upload a CSV/Excel file or click **✨ Use sample**.
3. Ask, e.g. *"Which category had the biggest revenue drop in September vs August, and which region caused most of it?"*
4. Watch the agents work, then **Approve** the answer or ask a follow-up.

Stop: `docker compose down` (add `-v` to also delete saved workspaces).

Without compose:
```bash
docker build -t datapilot:1.0 .
docker run --rm -p 8503:8501 datapilot:1.0
```

## Deploy to a VPS with HTTPS

```bash
cd /root/AI-B12-2/Week6-Day3-DataPilot/Pilot && git pull
BASIC_AUTH_USER=admin sudo -E bash deploy/deploy_vps.sh
```
Nginx + Let's Encrypt in front of the container, which is bound to `127.0.0.1` only. Details: [deploy/README-deploy.md](deploy/README-deploy.md).

## Run locally (without Docker)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```
> Outside Docker, AI-written code runs in `./workspaces/<session>` on your machine. Docker is the safer option.

## Configuration

| Where | Setting | Default |
|---|---|---|
| UI sidebar | OpenAI API key, model (`gpt-4.1-mini`, `gpt-4.1`, `gpt-4o`, `gpt-4o-mini`, `gpt-5-mini`, `gpt-5`, custom) | `gpt-4.1-mini` |
| UI sidebar → Advanced | Base URL for OpenAI-compatible endpoints | OpenAI |
| UI sidebar | Turn-taking: Selector / RoundRobin | Selector |
| UI sidebar | Safety limit (messages per run) | 12 |
| UI sidebar | Self-correction demo mode (Coder makes one deliberate mistake first) | off |
| Env | `DATAPILOT_EXEC_TIMEOUT` seconds per code execution | 90 |
| Env | `DATAPILOT_WORKSPACE` sandbox root | `/app/workspaces` |

## How it works

```
Ask → Plan (Planner) → Code (Coder) → Run (Executor) → Review (Reviewer) → Answer (you approve)
                         ▲                 │ error            │ feedback
                         └─────────────────┴──────────────────┘
Stop:  TextMentionTermination("APPROVED", sources=["Reviewer"]) | MaxMessageTermination(12)
```

| AutoGen part | Used for |
|---|---|
| `AssistantAgent` | Planner, Coder, Reviewer (one system message each) |
| `CodeExecutorAgent` + `LocalCommandLineCodeExecutor` | Runs the Coder's code inside the container sandbox folder |
| `SelectorGroupChat` (+ deterministic `selector_func`) / `RoundRobinGroupChat` | Turn-taking |
| `TextMentionTermination` \| `MaxMessageTermination` | Clean stopping, cost control |
| `UserProxyAgent` | Human approval / follow-up (input wired to the UI) |
| `team.save_state()` / `load_state()` | Follow-ups continue the same session |

See **[design.md](design.md)** for diagrams and **[PRD.md](PRD.md)** for requirements and acceptance criteria.

## Project structure

```
├── app.py                    # Streamlit UI (themed), live streaming, approval, downloads
├── datapilot/
│   ├── config.py             # names, models, limits, settings dataclass
│   ├── prompts.py            # system messages per agent
│   ├── team.py               # AutoGen agents, routing, termination, run loop, UserProxy
│   ├── workspace.py          # sandbox folder, dataset profile, re-run analysis.py
│   ├── report.py             # one-page PDF report
│   └── ui_theme.py           # aurora theme CSS, badges, pipeline stepper
├── sample_data/
│   ├── generate_sales.py     # deterministic generator (seeded)
│   └── sales_2026.csv        # 12,480 rows demo data
├── tests/test_agent_loop.py  # offline loop test (ReplayChatCompletionClient, no API key)
├── .streamlit/config.toml    # dark theme base
├── Dockerfile · docker-compose.yml · .dockerignore · requirements.txt
├── PRD.md · design.md · README.md
```

## Testing

```bash
python -m pytest -q tests
# or inside the container
docker compose exec datapilot python -m pytest -q tests
```
The test scripts a fake LLM so the Coder's first script fails with `KeyError`, and checks the team routes the
error back to the Coder, runs the fix, terminates on `APPROVED`, that re-running `analysis.py` gives identical
output, and that a follow-up continues from saved state.

## Done checklist

- [x] Agents fix a code error on their own (demo mode makes this reliable; also covered by the test)
- [x] Code runs only inside the sandbox folder / Docker container
- [x] Stops on APPROVED or after 12 messages
- [x] Re-running `analysis.py` gives the same numbers (*Re-run & verify*)
- [x] Every chart has a title, axis labels and units
- [x] Human approval works; follow-ups continue the same session
- [x] Stretch: SelectorGroupChat · multi-sheet Excel · PDF report

## Security notes
- Your API key lives only in the Streamlit session (memory); it is never written to disk or logs.
- Generated code runs as a non-root user in the container, in a per-session folder, with a timeout and CPU/RAM limits.
- Don't expose the container to the internet as-is: it has no authentication (it's meant for local Docker Desktop use).

## Troubleshooting
| Symptom | Fix |
|---|---|
| `AuthenticationError` | Check the key; click *Test key*. |
| `model_not_found` | Your account may not have that model; pick `gpt-4.1-mini` or `gpt-4o-mini`. |
| Run stops at the limit | Click **Continue** or raise the limit slider; try a stronger model. |
| Port 8503 busy | Set `DATAPILOT_PORT` (e.g. `8510`) before `docker compose up`. |
