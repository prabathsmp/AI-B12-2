"""DataPilot - Self-Correcting Data Analyst (Streamlit + Microsoft AutoGen AgentChat)."""
from __future__ import annotations

import asyncio
import html
import io
import re
import shutil
import time
import zipfile
from pathlib import Path

import streamlit as st

from datapilot.config import (
    CODER,
    DEFAULT_MAX_MESSAGES,
    EXECUTOR,
    MODEL_CHOICES,
    PLANNER,
    REVIEWER,
    ROUTING_CHOICES,
    SAMPLE_DATA,
    USER_PROXY,
    RunSettings,
)
from datapilot.report import build_pdf
from datapilot.team import RunOutcome, human_turn, is_execution_error, parse_final_answer, stream_analysis
from datapilot.ui_theme import AGENT_STYLE, CSS, badge, kpi, pipeline_html
from datapilot.workspace import Workspace, load_preview, profile_dataset

st.set_page_config(page_title="DataPilot", page_icon="🛰️", layout="wide", initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)

PROFILE_MARK = "---- DATASET PROFILE ----"
SAMPLE_QUESTIONS = [
    "Which category had the biggest revenue drop in September vs August, and which region caused most of it?",
    "Show monthly revenue trend for 2026 by category and name the best month.",
    "Which 5 products earn the most revenue after discount, and what share of total do they make?",
]

# ------------------------------------------------------------------ state
ss = st.session_state
ss.setdefault("ws", Workspace())
ss.setdefault("dataset", None)        # Path
ss.setdefault("dataset_sig", None)
ss.setdefault("profile", "")
ss.setdefault("team_state", None)     # AutoGen team state (dict) -> lets follow-ups continue the same session
ss.setdefault("transcript", [])       # [{run, source, content}]
ss.setdefault("runs", [])             # run records
ss.setdefault("pending", None)        # (kind, text)
ss.setdefault("key_ok", None)
ws: Workspace = ss.ws


def reset_session(keep_data: bool = True) -> None:
    ss.team_state, ss.transcript, ss.runs, ss.pending = None, [], [], None
    data = ss.dataset.read_bytes() if (keep_data and ss.dataset and ss.dataset.exists()) else None
    name = ss.dataset.name if ss.dataset else None
    ws.reset()
    if data and name:
        ss.dataset = ws.save_dataset(name, data)
    else:
        ss.dataset, ss.dataset_sig, ss.profile = None, None, ""


def set_dataset(name: str, content: bytes) -> None:
    sig = (name, len(content), hash(content[:4096]))
    if sig == ss.dataset_sig:
        return
    reset_session(keep_data=False)
    path = ws.save_dataset(name, content)
    try:
        ss.profile = profile_dataset(path, f"data/{path.name}")
    except Exception as e:  # noqa: BLE001
        st.sidebar.error(f"Could not read file: {e}")
        path.unlink(missing_ok=True)
        return
    ss.dataset, ss.dataset_sig = path, sig


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown(
        '<div class="side-brand"><div class="logo">🛰️</div><div><b>DataPilot</b>'
        "<small>Self-correcting AI data analyst</small></div></div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="side-step">① Connect OpenAI</div>', unsafe_allow_html=True)
    api_key = st.text_input("OpenAI API key", type="password", placeholder="sk-...", key="api_key",
                            help="Kept only in this browser session's memory. Never written to disk.")
    model = st.selectbox("Model", MODEL_CHOICES + ["custom…"], index=0)
    if model == "custom…":
        model = st.text_input("Custom model name", value="gpt-4.1-mini")
    with st.expander("Advanced endpoint"):
        base_url = st.text_input("Base URL (optional)", placeholder="https://api.openai.com/v1",
                                 help="For Azure-compatible / proxy / OpenAI-compatible endpoints.") or None
    c1, c2 = st.columns([1, 1])
    if c1.button("Test key", width="stretch", disabled=not api_key):
        try:
            from openai import OpenAI

            OpenAI(api_key=api_key, base_url=base_url, timeout=15).models.list()
            ss.key_ok = True
        except Exception as e:  # noqa: BLE001
            ss.key_ok = f"{type(e).__name__}: {str(e)[:120]}"
    if ss.key_ok is True and api_key:
        c2.markdown('<span class="status-pill st-ok">● Connected</span>', unsafe_allow_html=True)
    elif isinstance(ss.key_ok, str):
        c2.markdown('<span class="status-pill st-warn">● Failed</span>', unsafe_allow_html=True)
        st.caption(ss.key_ok)
    elif not api_key:
        c2.markdown('<span class="status-pill st-idle">● No key</span>', unsafe_allow_html=True)

    st.markdown('<div class="side-step">② Load data</div>', unsafe_allow_html=True)
    up = st.file_uploader("Sales CSV or Excel", type=["csv", "xlsx"], label_visibility="collapsed")
    if up is not None:
        set_dataset(up.name, up.getvalue())
    if st.button("✨ Use sample: sales_2026.csv (12,480 rows)", width="stretch"):
        set_dataset(SAMPLE_DATA.name, SAMPLE_DATA.read_bytes())

    st.markdown('<div class="side-step">③ Agent team</div>', unsafe_allow_html=True)
    routing = st.radio("Turn-taking", ROUTING_CHOICES, index=0,
                       help="Selector: errors go straight back to the Coder. RoundRobin: fixed Planner→Coder→Executor→Reviewer order.")
    max_messages = st.slider("Safety limit (messages per run)", 6, 20, DEFAULT_MAX_MESSAGES,
                             help="MaxMessageTermination - the run always stops here or on APPROVED.")
    stress = st.toggle("Self-correction demo mode", value=False,
                       help="Asks the Coder to make one deliberate mistake in its first draft so you can watch the error → fix loop.")

    st.markdown('<div class="side-step">Session</div>', unsafe_allow_html=True)
    if st.button("↺ New session (keep data)", width="stretch"):
        reset_session(keep_data=True)
        st.rerun()
    st.caption(f"Sandbox: `workspaces/{ws.session_id}` · Code only runs inside this folder.")

settings = RunSettings(api_key=api_key, model=model, base_url=base_url, routing=routing,
                       max_messages=max_messages, stress_test=stress)

# ------------------------------------------------------------------ hero
st.markdown(
    """
<div class="hero">
  <h1>Data<span>Pilot</span> · Self-Correcting Data Analyst</h1>
  <p>Ask a business question in plain English. A team of AutoGen agents plans, writes Python, runs it in a
  sandbox, fixes its own errors and returns a reviewed answer with charts and re-runnable code.</p>
  <div class="chip-row">
    <span class="chip">🧭 Planner</span><span class="chip">🛠️ Coder</span><span class="chip">⚙️ Executor (sandbox)</span>
    <span class="chip">🔍 Reviewer</span><span class="chip">🧑‍💼 You approve</span>
    <span class="chip">⛔ Stops on APPROVED or message limit</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------ helpers
def run_messages(run_idx: int) -> list[dict]:
    return [m for m in ss.transcript if m["run"] == run_idx]


def pipeline_state(msgs: list[dict], running: bool, run: dict | None) -> dict:
    srcs = [m["source"] for m in msgs]
    done, warn, loops = set(), set(), {}
    if msgs:
        done.add(0)
    if PLANNER in srcs:
        done.add(1)
    if CODER in srcs:
        done.add(2)
    exec_msgs = [m for m in msgs if m["source"] == EXECUTOR]
    if exec_msgs:
        done.add(3)
    if REVIEWER in srcs:
        done.add(4)
    errors = sum(1 for m in exec_msgs if is_execution_error(m["content"]))
    feedback = sum(1 for m in msgs if m["source"] == REVIEWER and "APPROVED" not in m["content"])
    if errors + feedback:
        loops[2] = errors + feedback
    active = None
    if running:
        last = srcs[-1] if srcs else "user"
        nxt = {"user": 1, PLANNER: 2, CODER: 3, REVIEWER: 2}.get(last)
        if last == EXECUTOR:
            nxt = 2 if is_execution_error(msgs[-1]["content"]) else 4
        active = nxt
    if run:
        if run["approved"]:
            done.add(4)
            if run.get("human") == "approved":
                done.add(5)
            else:
                active = 5
        else:
            warn.add(4)
    return {"done": done, "active": active, "warn": warn, "loops": loops}


def run_stats(msgs: list[dict]) -> tuple[int, int, int]:
    fixes = sum(1 for m in msgs if m["source"] == EXECUTOR and is_execution_error(m["content"]))
    reviews = sum(1 for m in msgs if m["source"] == REVIEWER)
    return len(msgs), fixes, reviews


CODE_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)


def render_message(m: dict, latest: bool) -> None:
    src, content = m["source"], m["content"]
    avatar = AGENT_STYLE.get(src, ("🤖",))[0]
    with st.chat_message(src if src in ("user", "assistant") else src, avatar=avatar):
        if src == "user":
            q, _, prof = content.partition(PROFILE_MARK)
            st.markdown(badge("user", "TASK"), unsafe_allow_html=True)
            st.markdown(q.strip())
            if prof:
                with st.expander("Dataset profile sent to the agents"):
                    st.code(prof.strip(), language="text")
        elif src == CODER:
            code = CODE_RE.search(content)
            prose = CODE_RE.sub("", content).strip()
            tag = "FIX" if prose.lower().startswith("fixed") else ("UPDATE" if prose.lower().startswith("updated") else "CODE")
            st.markdown(badge(src, tag), unsafe_allow_html=True)
            if prose:
                st.markdown(prose)
            if code:
                lines = code.group(1).count("\n")
                with st.expander(f"analysis.py · {lines} lines", expanded=latest):
                    st.code(code.group(1), language="python", line_numbers=True)
        elif src == EXECUTOR:
            err = is_execution_error(content)
            st.markdown(badge(src, "ERROR" if err else "OK"), unsafe_allow_html=True)
            text = content if len(content) < 6000 else content[:6000] + "\n… (truncated)"
            st.code(text, language="text")
        elif src == REVIEWER:
            ok = "APPROVED" in content
            st.markdown(badge(src, "APPROVED" if ok else "FEEDBACK"), unsafe_allow_html=True)
            st.markdown(content)
        else:
            st.markdown(badge(src), unsafe_allow_html=True)
            st.markdown(content)


def render_run_header(i: int, run: dict | None, question: str) -> None:
    status = ""
    if run:
        status = " · ✅ approved" if run["approved"] else " · ⚠ stopped at limit"
    st.markdown(f'<div class="run-sep">Run {i + 1}{html.escape(status)}</div>', unsafe_allow_html=True)


def snapshot_run(idx: int, started: float) -> tuple[list[Path], Path | None]:
    dest = ws.root / "runs" / f"run_{idx + 1}"
    dest.mkdir(parents=True, exist_ok=True)
    charts = []
    for p in ws.charts():
        if p.stat().st_mtime >= started - 1:
            shutil.copy2(p, dest / p.name)
            charts.append(dest / p.name)
    script = None
    if ws.script.exists() and ws.script.stat().st_mtime >= started - 1:
        script = dest / "analysis.py"
        shutil.copy2(ws.script, script)
    return charts, script


def bundle_zip(run: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in run["charts"]:
            z.write(p, p.name)
        if run["script"]:
            z.write(run["script"], "analysis.py")
        z.writestr("answer.md", run.get("final_text", ""))
    return buf.getvalue()


def compose_task(kind: str, text: str) -> str:
    if kind == "new":
        return f"BUSINESS QUESTION: {text}\n\n{PROFILE_MARK}\n{ss.profile}"
    if kind == "followup":
        return (f"FOLLOW-UP QUESTION (same dataset, same session): {text}\n"
                "Planner: write a fresh short plan. Coder: send a new complete analysis.py.")
    return "Continue: address the latest error or Reviewer feedback and finish the analysis."


# ------------------------------------------------------------------ guards / onboarding
ready = bool(api_key) and ss.dataset is not None
if not ready:
    a, b, c = st.columns(3)
    a.markdown(f'<div class="card"><div class="n">STEP 1</div><b>{"✅ " if api_key else ""}Plug in your OpenAI key</b>'
               "<p>Paste it in the sidebar. It stays in session memory only.</p></div>", unsafe_allow_html=True)
    b.markdown(f'<div class="card"><div class="n">STEP 2</div><b>{"✅ " if ss.dataset else ""}Upload a sales file</b>'
               "<p>CSV or multi-sheet Excel - or one click on the sample dataset.</p></div>", unsafe_allow_html=True)
    c.markdown('<div class="card"><div class="n">STEP 3</div><b>Ask in plain English</b>'
               "<p>Watch the agents plan, code, fail, fix and get reviewed - live.</p></div>", unsafe_allow_html=True)
    st.write("")

# ------------------------------------------------------------------ status strip
last_run = ss.runs[-1] if ss.runs else None
cur_idx = len(ss.runs) - 1 if ss.runs else 0
pipe_ph = st.empty()
kpi_ph = st.empty()


def draw_status(msgs: list[dict], running: bool, run: dict | None) -> None:
    pipe_ph.markdown(pipeline_html(pipeline_state(msgs, running, run)), unsafe_allow_html=True)
    n, fixes, reviews = run_stats(msgs)
    if running:
        pill = "Agents working…"
    elif run is None:
        pill = "Ready" if ready else "Setup needed"
    elif run["approved"]:
        pill = "Human approved" if run.get("human") == "approved" else "Awaiting your approval"
    else:
        pill = "Stopped at limit"
    with kpi_ph.container():
        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(kpi("Status", pill), unsafe_allow_html=True)
        k2.markdown(kpi("Messages this run", str(n), f"/ {settings.max_messages}"), unsafe_allow_html=True)
        k3.markdown(kpi("Self-fixes", str(fixes), "errors repaired"), unsafe_allow_html=True)
        k4.markdown(kpi("Review rounds", str(reviews), f"· {len(ss.runs)} run(s)"), unsafe_allow_html=True)


draw_status(run_messages(cur_idx) if ss.runs else [], False, last_run)

# ------------------------------------------------------------------ tabs
t_conv, t_ans, t_charts, t_code, t_data = st.tabs(
    ["🧠 Agent conversation", "✅ Answer", "📊 Charts", "🧾 analysis.py", "🗂️ Data"]
)

with t_data:
    if ss.dataset:
        frames = load_preview(ss.dataset)
        st.markdown(f"**{ss.dataset.name}** · " + " · ".join(f"{(s or 'table')}: {len(df):,} rows × {df.shape[1]} cols" for s, df in frames.items()))
        for s, df in frames.items():
            if s:
                st.markdown(f"#### Sheet: {s}")
            st.dataframe(df.head(200), width="stretch", height=320)
        with st.expander("Profile given to the agents"):
            st.code(ss.profile, language="text")
    else:
        st.info("No dataset loaded yet - use the sidebar.")

with t_ans:
    if not last_run:
        st.info("The reviewed answer appears here once the Reviewer says **APPROVED**.")
    for i in range(len(ss.runs) - 1, -1, -1):
        run = ss.runs[i]
        st.markdown(f"##### Run {i + 1} · {html.escape(run['question'])}")
        if not run["approved"]:
            st.warning(f"Run stopped without approval ({run['stop_reason']}). Use **Continue** in the conversation tab.")
            continue
        sec = run["sections"]
        nxt = sec.get("SUGGESTED NEXT QUESTION", "")
        st.markdown(
            '<div class="answer-card">'
            f'<h4>Answer</h4><div class="big">{html.escape(sec.get("ANSWER", ""))}</div>'
            + (f'<h4 style="margin-top:1rem">Where it came from</h4><div class="src">{html.escape(sec.get("WHERE IT CAME FROM", ""))}</div>' if sec.get("WHERE IT CAME FROM") else "")
            + (f'<h4 style="margin-top:1rem">Files</h4><div class="src">{html.escape(sec.get("FILES", ""))}</div>' if sec.get("FILES") else "")
            + (f'<div class="next-q">💡 <b>Suggested next question:</b> {html.escape(nxt)}</div>' if nxt else "")
            + "</div>",
            unsafe_allow_html=True,
        )
        d1, d2, d3 = st.columns(3)
        d1.download_button("⬇ PDF report", build_pdf(run["question"], sec, run["charts"]), f"datapilot_run{i + 1}.pdf",
                           "application/pdf", width="stretch", key=f"pdf{i}", type="primary")
        d2.download_button("⬇ Charts + code (.zip)", bundle_zip(run), f"datapilot_run{i + 1}.zip", "application/zip",
                           width="stretch", key=f"zip{i}")
        if nxt and i == len(ss.runs) - 1 and d3.button("Ask suggested question →", width="stretch", key=f"nq{i}"):
            ss.pending = ("followup", nxt)
            st.rerun()

with t_charts:
    shown = False
    for i in range(len(ss.runs) - 1, -1, -1):
        charts = ss.runs[i]["charts"]
        if not charts:
            continue
        shown = True
        st.markdown(f"##### Run {i + 1} · {html.escape(ss.runs[i]['question'])}")
        cols = st.columns(2)
        for j, p in enumerate(charts):
            with cols[j % 2]:
                st.image(str(p), width="stretch", caption=p.name)
                st.download_button(f"⬇ {p.name}", p.read_bytes(), p.name, "image/png", key=f"c{i}{j}", width="stretch")
    if not shown:
        st.info("Charts (PNG) saved by analysis.py show up here.")

with t_code:
    runs_with_code = [(i, r) for i, r in enumerate(ss.runs) if r["script"]]
    if not runs_with_code:
        st.info("The final working analysis.py appears here.")
    else:
        labels = [f"Run {i + 1} · {r['question'][:70]}" for i, r in runs_with_code][::-1]
        pick = st.selectbox("Script from", labels)
        i, r = runs_with_code[::-1][labels.index(pick)]
        code = r["script"].read_text(encoding="utf-8")
        b1, b2 = st.columns([1, 1])
        b1.download_button("⬇ Download analysis.py", code, "analysis.py", "text/x-python", width="stretch", type="primary")
        if b2.button("▶ Re-run & verify numbers", width="stretch"):
            with st.spinner("Re-running analysis.py in the sandbox…"):
                rc, out = ws.rerun_script(r["script"])
            norm = lambda s: [ln.rstrip() for ln in s.strip().splitlines()]  # noqa: E731
            if rc != 0:
                st.error("Re-run failed.")
            elif norm(out) == norm(r.get("exec_output", "")):
                st.success("✅ Reproducible: re-running analysis.py gives exactly the same output as the approved run.")
            else:
                st.warning("Output differs from the approved run - compare below.")
            st.code(out, language="text")
        st.code(code, language="python", line_numbers=True)

# ------------------------------------------------------------------ conversation + live run
with t_conv:
    if not ss.transcript and not ss.pending:
        st.markdown("##### Try one of these")
        qc = st.columns(len(SAMPLE_QUESTIONS))
        for j, q in enumerate(SAMPLE_QUESTIONS):
            if qc[j].button(q, width="stretch", disabled=not ready, key=f"sq{j}"):
                ss.pending = ("new", q)
                st.rerun()

    for i in range(len(ss.runs) + (1 if ss.pending else 0)):
        msgs = run_messages(i)
        if not msgs:
            continue
        render_run_header(i, ss.runs[i] if i < len(ss.runs) else None, "")
        for k, m in enumerate(msgs):
            render_message(m, latest=(i == len(ss.runs) - 1 and k == len(msgs) - 1))
    live_area = st.container()

    # ---- human-in-the-loop panel
    if last_run and not ss.pending:
        if last_run["approved"] and last_run.get("human") != "approved":
            st.markdown('<div class="run-sep">Your decision</div>', unsafe_allow_html=True)
            h1, h2 = st.columns([1, 2])
            if h1.button("👍 Approve final answer", type="primary", width="stretch"):
                reply = asyncio.run(human_turn("APPROVE"))
                last_run["human"] = "approved"
                ss.transcript.append({"run": cur_idx, "source": USER_PROXY, "content": f"✅ {reply} - final answer accepted."})
                st.rerun()
            h2.markdown('<div class="next-q">…or type a follow-up question below - the same agent session continues with full memory.</div>',
                        unsafe_allow_html=True)
        elif not last_run["approved"]:
            st.warning(f"Stopped without APPROVED ({last_run['stop_reason']}). The safety limit prevents endless loops.")
            if st.button(f"▶ Continue for another {settings.max_messages} messages", type="primary"):
                ss.pending = ("continue", "Continue the previous analysis")
                st.rerun()

    # ---- execute a pending task
    if ss.pending and ready:
        kind, text = ss.pending
        if ss.team_state is None:
            kind = "new"
        idx = len(ss.runs)
        started = time.time()
        task = compose_task(kind, text)
        if kind == "followup":
            # The human's follow-up goes through AutoGen's UserProxyAgent; the team then resumes from saved state.
            text = asyncio.run(human_turn(text))
            task = compose_task(kind, text)
        live_msgs: list[dict] = []

        with live_area:
            render_run_header(idx, None, text)
            draw_status([], True, None)
            holder: dict = {}

            async def go() -> None:
                async for item in stream_analysis(settings, ws, task, ss.team_state):
                    if isinstance(item, RunOutcome):
                        holder["outcome"] = item
                        continue
                    content = item.to_text() if item.source != "user" else task
                    if item.source == "user" and kind != "new":
                        content = text if kind == "followup" else "▶ Continue the previous analysis."
                    m = {"run": idx, "source": item.source, "content": content}
                    live_msgs.append(m)
                    ss.transcript.append(m)
                    render_message(m, latest=True)
                    draw_status(live_msgs, True, None)

            try:
                with st.spinner("Agents are collaborating…"):
                    asyncio.run(go())
            except Exception as e:  # noqa: BLE001
                holder["error"] = e

        ss.pending = None
        outcome: RunOutcome | None = holder.get("outcome")
        error: Exception | None = holder.get("error")
        if error or outcome is None:
            # drop partial run messages so the session stays consistent
            ss.transcript = [m for m in ss.transcript if m["run"] != idx]
            st.error(f"Run failed: {type(error).__name__ if error else 'no result'} - {str(error)[:400] if error else ''}")
            st.caption("Check the API key / model name in the sidebar, then try again.")
        else:
            charts, script = snapshot_run(idx, started)
            exec_ok = [m["content"] for m in live_msgs if m["source"] == EXECUTOR and not is_execution_error(m["content"])]
            ss.team_state = outcome.state
            ss.runs.append({
                "question": text,
                "approved": outcome.approved,
                "stop_reason": outcome.stop_reason,
                "final_text": outcome.final_text,
                "sections": parse_final_answer(outcome.final_text) if outcome.approved else {},
                "charts": charts,
                "script": script,
                "exec_output": exec_ok[-1] if exec_ok else "",
                "human": None,
            })
            st.rerun()
    elif ss.pending and not ready:
        ss.pending = None

# ------------------------------------------------------------------ chat input
placeholder = (
    "Ask a follow-up question - same session, full memory…" if (last_run and ss.team_state)
    else "Ask a business question about your data…"
)
prompt = st.chat_input(placeholder if ready else "Add your API key and a dataset in the sidebar to start", disabled=not ready)
if prompt:
    ss.pending = ("followup" if ss.team_state else "new", prompt)
    st.rerun()
