"""LaunchScout - Streamlit UI for the competitor research crew."""
from __future__ import annotations

import queue
import re
import threading
import time
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from scout import theme  # noqa: E402
from scout.config import Settings, mask  # noqa: E402
from scout.crew import AGENTS, SECTIONS, run_crew  # noqa: E402
from scout.pdf import markdown_to_pdf  # noqa: E402

st.set_page_config(page_title="LaunchScout · Competitor Research Crew", page_icon="🛰️", layout="wide")
st.markdown(theme.CSS, unsafe_allow_html=True)

NAMES = {a["key"]: a["name"] for a in AGENTS}
ICONS = {a["key"]: a["icon"] for a in AGENTS}
SAMPLES = {
    "🥗 Millet meal boxes · Coimbatore": ("Healthy millet meal boxes delivered for lunch", "Coimbatore",
                                         "Office workers, age 25 to 40", ""),
    "☕ Specialty coffee cart · Pune": ("Specialty filter-coffee cart at tech parks", "Pune",
                                       "IT professionals and students, age 20 to 35", ""),
    "🐾 Pet grooming at home · Bengaluru": ("At-home pet grooming service", "Bengaluru",
                                           "Working pet parents in apartments", ""),
}

ss = st.session_state
ss.setdefault("status", {a["key"]: "waiting" for a in AGENTS})
ss.setdefault("counts", {})
ss.setdefault("log", [])
ss.setdefault("result", None)
ss.setdefault("error", None)
for k in ("idea", "city", "customer", "known"):
    ss.setdefault(k, "")


def load_sample() -> None:
    if ss.get("sample") in SAMPLES:
        ss.idea, ss.city, ss.customer, ss.known = SAMPLES[ss.sample]


# ---------------------------------------------------------------- sidebar
env = Settings()
with st.sidebar:
    st.markdown("### ⚙️ Crew settings")
    st.caption("Keys are pluggable: set them in `.env` or paste here. Pasted keys live only in this browser session.")
    api_key = st.text_input("OpenAI API key", type="password", placeholder="sk-… (uses .env if blank)")
    model = st.text_input("Model", value=env.model, help="Any OpenAI chat model, e.g. gpt-4o-mini, gpt-4.1, gpt-4o")
    base_url = st.text_input("Base URL (optional)", value=env.base_url,
                             help="OpenAI-compatible endpoint: Azure, OpenRouter, local LLM server…")
    serper = st.text_input("Serper API key (optional)", type="password",
                           placeholder="uses .env if blank; DuckDuckGo if none")
    hierarchical = st.toggle("Hierarchical process (stretch)", value=False,
                             help="A manager LLM delegates to the agents instead of a fixed order.")
    temperature = st.slider("Creativity", 0.0, 1.0, 0.3, 0.1)

    settings = Settings(
        openai_api_key=(api_key or env.openai_api_key).strip(),
        model=(model or env.model).strip(),
        base_url=(base_url or "").strip(),
        serper_api_key=(serper or env.serper_api_key).strip(),
        temperature=temperature,
        hierarchical=hierarchical,
    )
    st.markdown("---")
    key_pill = "ok" if settings.has_llm_key else "warn"
    st.markdown(
        f'<span class="pill {key_pill}">LLM key: {mask(settings.openai_api_key)}</span>&nbsp;'
        f'<span class="pill {"ok" if settings.serper_api_key else "warn"}">Search: {settings.search_provider}</span>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.caption("Process: " + ("Hierarchical (manager delegates)" if hierarchical else "Sequential (task → task)"))

# ---------------------------------------------------------------- header
st.markdown(theme.hero(settings.search_provider, settings.model), unsafe_allow_html=True)
st.markdown(theme.pipeline(), unsafe_allow_html=True)

left, right = st.columns([5, 7], gap="large")

with left:
    st.markdown(theme.section_title("Founder brief"), unsafe_allow_html=True)
    st.pills("Try a sample brief", list(SAMPLES), key="sample", on_change=load_sample)
    with st.form("brief"):
        st.text_input("Business idea *", key="idea", placeholder="e.g. Healthy millet meal boxes delivered for lunch")
        c1, c2 = st.columns(2)
        c1.text_input("City *", key="city", placeholder="e.g. Coimbatore")
        c2.text_input("Target customer *", key="customer", placeholder="e.g. Office workers, 25-40")
        st.text_area("Known competitors (optional)", key="known", height=80,
                     placeholder="Comma separated, leave blank to let the crew discover them")
        submitted = st.form_submit_button("🚀  Launch the crew", use_container_width=True)

with right:
    st.markdown(theme.section_title("Crew at work"), unsafe_allow_html=True)
    cards_ph = st.empty()
    st.markdown(theme.section_title("Live activity"), unsafe_allow_html=True)
    log_ph = st.empty()


def render_live() -> None:
    cards_ph.markdown(theme.agent_cards(AGENTS, ss.status, ss.counts), unsafe_allow_html=True)
    log_ph.markdown(theme.activity_log(ss.log, NAMES), unsafe_allow_html=True)


def add_log(agent: str | None, text: str, tool: str | None = None, icon: str | None = None) -> None:
    ss.log.append({"time": datetime.now().strftime("%H:%M:%S"), "agent": agent, "text": text,
                   "tool": tool, "icon": icon or ICONS.get(agent, "🛰️")})


def handle(ev: dict) -> None:
    kind, agent = ev.get("type"), ev.get("agent")
    if kind == "start":
        add_log(None, f"Crew assembled. Searching the web via {ev['search']}.", icon="🛰️")
    elif kind == "agent_start":
        ss.status[agent] = "working"
        add_log(agent, "Picked up the task and started working.", icon="▶️")
    elif kind in ("tool_start", "tool_done", "tool_error", "step"):
        if ss.status.get(agent) != "done":
            ss.status[agent] = "working"
        if kind == "tool_start":
            ss.counts[agent] = ss.counts.get(agent, 0) + 1
            add_log(agent, f"Using tool → {ev.get('input')}", tool=ev.get("tool"), icon="🛠️")
        elif kind == "tool_done":
            res = ev.get("result") or ""
            if res.startswith(("Search failed", "Could not scrape", "No results")):
                add_log(agent, f"Tool hiccup (agent will retry): {res}", tool=ev.get("tool"), icon="⚠️")
            else:
                add_log(agent, f"Found ⟶ {res}", tool=ev.get("tool"), icon="📥")
        elif kind == "tool_error":
            add_log(agent, f"Tool hiccup (continuing): {ev.get('result')}", tool=ev.get("tool"), icon="⚠️")
        elif ev.get("kind") == "finish":
            add_log(agent, "Drafted findings: " + (ev.get("result") or ""), icon="📝")
    elif kind == "task_done":
        ss.status[agent] = "done"
        preview = " ".join((ev.get("output") or "").split())[:240]
        add_log(agent, f"Delivered: {preview}…", icon="✅")


def report_stats(report: str) -> dict:
    urls = set(re.findall(r"https?://[^\s\)\]>|,]+", report))
    sec1 = re.split(r"\n##\s*2\.", report.split("## 1.", 1)[-1])[0] if "## 1." in report else ""
    rows = [ln for ln in sec1.splitlines() if ln.strip().startswith("|")]
    competitors = max(len(rows) - 2, 0)
    found = sum(1 for s in SECTIONS if re.search(rf"^##\s*\d*\.?\s*{re.escape(s)}", report, re.I | re.M))
    return {"urls": len(urls), "competitors": competitors, "sections": found}


# ---------------------------------------------------------------- run
if submitted:
    missing = [n for n, v in (("Business idea", ss.idea), ("City", ss.city), ("Target customer", ss.customer)) if not v.strip()]
    if missing:
        st.toast("Please fill: " + ", ".join(missing), icon="⚠️")
        ss.error = "Please fill in: " + ", ".join(missing)
    elif not settings.has_llm_key:
        ss.error = "No OpenAI API key found. Add OPENAI_API_KEY to .env or paste one in the sidebar."
    else:
        ss.error, ss.result = None, None
        ss.status = {a["key"]: "waiting" for a in AGENTS}
        ss.counts, ss.log = {}, []
        inputs = {"idea": ss.idea.strip(), "city": ss.city.strip(), "customer": ss.customer.strip(),
                  "known_competitors": ss.known.strip() or "None provided"}
        events: queue.Queue = queue.Queue()

        def worker() -> None:
            try:
                events.put({"type": "result", "data": run_crew(settings, inputs, events.put)})
            except Exception as exc:  # surface any failure to the UI
                events.put({"type": "error", "message": f"{type(exc).__name__}: {exc}"})

        started = time.time()
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        final = None
        with right:
            spinner_ph = st.empty()
        while final is None:
            try:
                while True:
                    ev = events.get_nowait()
                    if ev["type"] in ("result", "error"):
                        final = ev
                        break
                    handle(ev)
            except queue.Empty:
                pass
            elapsed = int(time.time() - started)
            spinner_ph.caption(f"⏱️ Running for {elapsed // 60}m {elapsed % 60:02d}s · agents are researching live")
            render_live()
            if final is None:
                if not thread.is_alive() and events.empty():
                    final = {"type": "error", "message": "The crew stopped unexpectedly."}
                time.sleep(0.5)
        spinner_ph.empty()
        if final["type"] == "result":
            data = final["data"]
            data["elapsed"] = int(time.time() - started)
            data["inputs"] = inputs
            ss.result = data
            ss.status = {a["key"]: "done" for a in AGENTS}
            add_log(None, f"Report ready and saved to {data['report_path']}", icon="🎉")
        else:
            ss.error = final["message"]
            for k, v in ss.status.items():
                if v == "working":
                    ss.status[k] = "error"
            add_log(None, "Crew failed: " + final["message"], icon="❌")
        st.rerun()

render_live()

# ---------------------------------------------------------------- results
st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
st.markdown(theme.section_title("Competitor report"), unsafe_allow_html=True)

if ss.error:
    st.error(ss.error, icon="🚨")

result = ss.result
if not result:
    st.markdown(theme.empty_state(), unsafe_allow_html=True)
else:
    report = result["report"]
    s = report_stats(report)
    st.markdown(theme.stats([
        ("Competitors", str(s["competitors"])),
        ("Source links", str(s["urls"])),
        ("Sections", f"{s['sections']}/6"),
        ("Run time", f"{result['elapsed'] // 60}m {result['elapsed'] % 60:02d}s"),
    ]), unsafe_allow_html=True)

    slug = re.sub(r"[^a-z0-9]+", "-", f"{result['inputs']['idea']} {result['inputs']['city']}".lower()).strip("-")[:60]
    d1, d2, d3 = st.columns([1, 1, 2])
    d1.download_button("⬇️  Download Markdown", report, file_name=f"{slug or 'report'}.md",
                       mime="text/markdown", use_container_width=True)
    try:
        pdf_bytes = markdown_to_pdf(report)
        d2.download_button("⬇️  Download PDF", pdf_bytes, file_name=f"{slug or 'report'}.pdf",
                           mime="application/pdf", use_container_width=True)
    except Exception as exc:
        d2.warning(f"PDF unavailable: {exc}")
    d3.caption(f"💾 Saved to `{result['report_path']}`" + (f" · 🔢 {result['tokens']:,} tokens" if result.get("tokens") else ""))

    tab_report, tab_agents, tab_raw = st.tabs(["📄 Report", "🤖 Agent outputs", "🧾 Markdown source"])
    with tab_report:
        with st.container(key="report"):
            st.markdown(report)
    with tab_agents:
        for a in AGENTS:
            with st.expander(f"{a['icon']}  {a['name']}", expanded=False):
                st.markdown(result["outputs"].get(a["key"]) or "_No output_")
    with tab_raw:
        st.code(report, language="markdown")

st.markdown('<div class="footer">LaunchScout · CrewAI multi-agent research · verify every number with its source</div>',
            unsafe_allow_html=True)
