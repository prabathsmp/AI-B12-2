# PRD — DataPilot: Self-Correcting Data Analyst

| | |
|---|---|
| **Track** | 3 · Agentic AI · AutoGen |
| **Level** | Intermediate |
| **Interface** | Streamlit chat web app (Docker-ready) |
| **Core skill** | Agent loops + sandboxed code execution |
| **Source** | `Requirement.docx` (Use Case 03) |
| **Version / date** | 1.0 · 21 Nov 2026 |

---

## 1. Problem statement

A retail business owner has a year of sales data in Excel/CSV and asks questions like *"Which category dropped
the most last month, and which region caused it?"*. They cannot write Python or SQL, so they wait days for an
analyst. Ordinary chatbots **guess** numbers. DataPilot **calculates** them: a team of AI agents writes real
pandas code, runs it in a sandbox, repairs its own errors and has the result reviewed before a human sees it.

### Why this is *Agentic* AI (not a fixed pipeline)
The agents choose the path at run time. If the code fails, the Coder reads the traceback and rewrites it; if the
Reviewer is not satisfied, work returns to the Coder. The loop continues until the goal is met (`APPROVED`) or a
safety limit is reached (12 messages).

## 2. Users & personas

| Persona | Need | Success looks like |
|---|---|---|
| Business owner | Fast, trustworthy answers with no code | Plain-English answer with exact numbers in < 2 min |
| Sales manager | Drill into category / region / product drivers | Breakdown of *where* a change came from + charts |
| Operations head | Re-usable, auditable analysis | Downloadable `analysis.py` that reproduces the numbers |

## 3. Goals & non-goals

**Goals**
- G1 Answer business questions on any uploaded sales CSV/Excel with numbers computed by code, not the LLM.
- G2 Show the complete agent conversation live, including errors and fixes (transparency).
- G3 Self-correct code errors with no human debugging.
- G4 Keep a human in charge of the final answer; allow follow-up questions in the same session.
- G5 Guarantee termination and bounded cost.
- G6 Run locally with one command on Docker Desktop; OpenAI key supplied by the user in the UI.

**Non-goals (v1)**: multi-user auth, database connectors, persistent cloud storage, fine-tuned models.

## 4. Agents (one clear job each)

| Agent | AutoGen class | Job |
|---|---|---|
| **Planner** | `AssistantAgent` | Reads the question + data profile, writes a 3–7 step analysis plan with formulas and the charts needed. |
| **Coder** | `AssistantAgent` | Writes a complete `analysis.py` (pandas + matplotlib). Rewrites it when it gets an error or feedback. |
| **Executor** | `CodeExecutorAgent` + `LocalCommandLineCodeExecutor` | Runs the Coder's code inside the session sandbox folder (inside the Docker container); returns output or error. |
| **Reviewer** | `AssistantAgent` | Checks: does it answer the question? numbers sensible? charts titled/labelled with units? Replies `APPROVED` (with the final answer) or `FEEDBACK`. |
| **User Proxy** | `UserProxyAgent` | The human. Approves the final answer or asks a follow-up question. |

## 5. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-1 | User enters their **OpenAI API key** in the UI (password field, session-memory only) and can test it. Model selectable; optional custom base URL. | Must |
| FR-2 | Upload **CSV** or **Excel (multi-sheet)**; one-click sample dataset `sales_2026.csv` (12,480 rows). | Must |
| FR-3 | Dataset is profiled (columns, dtypes, ranges, categories, sample rows) and given to the agents. | Must |
| FR-4 | User asks a question in plain English via chat input or suggestion chips. | Must |
| FR-5 | Team runs Planner → Coder → Executor → Reviewer; on Executor error or Reviewer feedback it loops back to the Coder automatically. | Must |
| FR-6 | Termination: `TextMentionTermination("APPROVED", sources=[Reviewer]) \| MaxMessageTermination(12)`. | Must |
| FR-7 | Agent conversation is streamed live with per-agent colour badges and tags (CODE / FIX / ERROR / OK / FEEDBACK / APPROVED). | Must |
| FR-8 | Final answer card: ANSWER, WHERE IT CAME FROM, FILES, SUGGESTED NEXT QUESTION. | Must |
| FR-9 | Charts saved as PNG (title, axis labels, units) and shown in a gallery with downloads. | Must |
| FR-10 | Final working `analysis.py` viewable/downloadable, with **Re-run & verify** that proves identical numbers. | Must |
| FR-11 | Human approval step (Approve) and follow-up question that continues the **same** agent session (team state saved/loaded). | Must |
| FR-12 | If the limit is hit without approval, the user can **Continue** for another bounded run. | Should |
| FR-13 | Routing choice: `SelectorGroupChat` (smart, default) or `RoundRobinGroupChat` (classic). | Should (stretch) |
| FR-14 | Export answer + charts as a one-page **PDF report**; zip of charts + code. | Should (stretch) |
| FR-15 | "Self-correction demo mode" toggle to reliably demonstrate the error → fix loop. | Could |

## 6. Non-functional requirements

| Area | Requirement |
|---|---|
| Safety | AI code runs only in `workspaces/<session>` inside the container, as a non-root user, with a per-execution timeout (90 s) and container CPU/RAM limits. Executor only executes code authored by the Coder. |
| Cost / termination | Hard cap of 12 messages per run (configurable 6–20); never loops forever. |
| Reproducibility | Scripts must be deterministic; re-running `analysis.py` yields the same output. |
| Privacy | API key never written to disk or logs; held in Streamlit session memory only. |
| UX | Dark "aurora" theme, glass panels, high-contrast text (≥ 4.5:1), live pipeline stepper, KPI strip, responsive layout. A plain/boring UI is out of scope. |
| Deployability | `docker compose up --build` on Docker Desktop → http://localhost:8503. Health check included. |

## 7. User flow

1. Paste OpenAI key → (Test key) → pick model.
2. Upload CSV/Excel or click **Use sample**.
3. Ask a question (type, or click a suggestion).
4. Watch: Planner plan → Coder code → Executor run (ERROR → Coder "Fixed:" → OK) → Reviewer feedback/APPROVED.
5. Read the answer card, charts and `analysis.py`; optionally **Re-run & verify**, download PDF/zip.
6. **Approve** the answer, or type a follow-up → the same session continues with full memory.

## 8. Sample acceptance scenario

Input: `sales_2026.csv` + *"Which category had the biggest revenue drop in September vs August, and which region
caused most of it?"*
Expected: Electronics identified as the biggest drop with Aug/Sep revenue and % change; South identified as the
main driver with its share; ≥ 1 labelled chart; `analysis.py` reproduces the numbers; suggested next question.

## 9. Done checklist (acceptance criteria)

- [x] At least one run shows the agents fixing a code error on their own (verified in `tests/test_agent_loop.py`; demo toggle in UI).
- [x] Code runs only inside the sandbox folder / Docker container.
- [x] Run stops on APPROVED or after 12 messages — never loops forever.
- [x] Re-running the saved `analysis.py` gives exactly the same numbers (Re-run & verify button).
- [x] Every chart has a title, axis labels and units (Coder rules + Reviewer check on `CHART |` lines).
- [x] Human approval works and a follow-up question continues the same session.
- [x] Stretch: SelectorGroupChat · Excel multi-sheet · one-page PDF report.

## 10. Tech stack

Python 3.12 · AutoGen AgentChat 0.7.5 (`autogen-agentchat`, `autogen-ext[openai]`) · OpenAI Chat Completions ·
pandas · matplotlib · Streamlit 1.50 · fpdf2 · Docker / Docker Compose.

## 11. Risks & mitigations

| Risk | Mitigation |
|---|---|
| LLM hallucinates numbers in the final answer | Reviewer must use only numbers printed in the `=== RESULTS ===` block; numbers come from code. |
| Generated code is unsafe / runs forever | Container sandbox, non-root user, timeout, resource limits, message cap. |
| Round-robin wastes turns on errors | Default SelectorGroupChat with deterministic `selector_func` routes errors straight back to the Coder. |
| Model/API errors | Friendly error panel; partial run discarded; key test button. |

## 12. Future scope
Docker-in-Docker executor (`DockerCommandLineCodeExecutor`), SQL/warehouse connectors, multi-user auth,
saved analysis library, scheduled reports.
