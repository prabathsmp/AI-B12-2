"""Visual theme: deep-space aurora background, glass panels, high-contrast text."""
from __future__ import annotations

import html

from .config import CODER, EXECUTOR, PLANNER, REVIEWER, USER_PROXY

AGENT_STYLE = {
    "user": ("🧑‍💼", "You", "#F472B6"),
    USER_PROXY: ("🧑‍💼", "You (UserProxy)", "#F472B6"),
    PLANNER: ("🧭", "Planner", "#A78BFA"),
    CODER: ("🛠️", "Coder", "#38BDF8"),
    EXECUTOR: ("⚙️", "Executor", "#FBBF24"),
    REVIEWER: ("🔍", "Reviewer", "#34D399"),
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

:root{
  --bg-0:#060914; --bg-1:#0B1124; --panel:rgba(20,28,56,.72); --panel-solid:#141C38;
  --stroke:rgba(148,163,255,.18); --stroke-strong:rgba(148,163,255,.38);
  --text:#EEF2FF; --muted:#A9B4D6; --cyan:#22D3EE; --violet:#A78BFA; --pink:#F472B6;
  --green:#34D399; --amber:#FBBF24; --red:#F87171;
}

html, body, [class*="css"], .stMarkdown, .stText, p, li, label, span, div { font-family:'Plus Jakarta Sans',system-ui,sans-serif; }
code, pre, .stCode, [data-testid="stCode"] * { font-family:'JetBrains Mono',ui-monospace,monospace !important; }

/* ---------- aurora background ---------- */
.stApp{
  background:
    radial-gradient(1100px 600px at 8% -10%, rgba(124,58,237,.35), transparent 60%),
    radial-gradient(900px 520px at 100% 0%, rgba(34,211,238,.22), transparent 55%),
    radial-gradient(800px 600px at 50% 110%, rgba(244,114,182,.16), transparent 60%),
    linear-gradient(180deg, var(--bg-0) 0%, var(--bg-1) 100%) !important;
  background-attachment: fixed !important;
  color: var(--text);
}
.stApp::before{ /* subtle grid */
  content:""; position:fixed; inset:0; pointer-events:none; z-index:0;
  background-image: linear-gradient(rgba(148,163,255,.05) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(148,163,255,.05) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: radial-gradient(ellipse at center, black 35%, transparent 80%);
}
[data-testid="stHeader"]{ background:transparent !important; }
[data-testid="stAppViewContainer"] > .main .block-container, .block-container{ padding-top:1.6rem; max-width:1280px; }
[data-testid="stBottomBlockContainer"], [data-testid="stBottom"] > div { background:transparent !important; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"]{
  background: linear-gradient(180deg, rgba(17,24,52,.96), rgba(10,14,32,.98)) !important;
  border-right:1px solid var(--stroke);
}
[data-testid="stSidebar"] *{ color:var(--text); }
[data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] small{ color:var(--muted) !important; }
.side-brand{display:flex;align-items:center;gap:.7rem;padding:.2rem 0 1rem 0;border-bottom:1px solid var(--stroke);margin-bottom:.8rem}
.side-brand .logo{width:42px;height:42px;border-radius:12px;display:grid;place-items:center;font-size:1.4rem;
  background:linear-gradient(135deg,#7C3AED,#22D3EE);box-shadow:0 8px 24px rgba(34,211,238,.35)}
.side-brand b{font-size:1.15rem;letter-spacing:.2px} .side-brand small{display:block;color:var(--muted);font-size:.74rem}
.side-step{font-size:.72rem;font-weight:800;letter-spacing:1.6px;text-transform:uppercase;color:var(--cyan);margin:1.1rem 0 .35rem}

/* ---------- inputs: always clearly visible ---------- */
.stTextInput input, .stTextArea textarea, .stNumberInput input,
[data-baseweb="select"] > div, [data-baseweb="input"]{
  background:#0E1530 !important; color:var(--text) !important; border:1px solid var(--stroke-strong) !important; border-radius:10px !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder{ color:#7D89B0 !important; }
.stTextInput input:focus, .stTextArea textarea:focus{ border-color:var(--cyan) !important; box-shadow:0 0 0 3px rgba(34,211,238,.2) !important; }
[data-baseweb="popover"] li, [data-baseweb="menu"]{ background:#111936 !important; color:var(--text) !important; }
label, .stRadio label, .stCheckbox label, .stToggle label, [data-testid="stWidgetLabel"] p{ color:var(--text) !important; font-weight:600 !important; }
[data-testid="stFileUploaderDropzone"]{ background:rgba(34,211,238,.06) !important; border:1.5px dashed rgba(34,211,238,.55) !important; border-radius:14px !important; }
[data-testid="stFileUploaderDropzone"] *{ color:var(--text) !important; }
[data-testid="stChatInput"]{ border-radius:16px !important; border:1px solid var(--stroke-strong) !important; background:#0E1530 !important;
  box-shadow:0 10px 40px rgba(124,58,237,.25); }
[data-testid="stChatInput"] textarea{ color:var(--text) !important; }

/* ---------- buttons ---------- */
.stButton > button, .stDownloadButton > button{
  border-radius:11px !important; font-weight:700 !important; border:1px solid var(--stroke-strong) !important;
  background:rgba(30,41,82,.85) !important; color:var(--text) !important; transition:all .18s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover{ border-color:var(--cyan) !important; color:#fff !important;
  box-shadow:0 0 0 3px rgba(34,211,238,.18), 0 8px 24px rgba(34,211,238,.18); transform:translateY(-1px); }
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"]{
  background:linear-gradient(135deg,#7C3AED 0%,#2563EB 55%,#06B6D4 100%) !important; border:none !important; color:#fff !important;
  box-shadow:0 10px 28px rgba(37,99,235,.38); }

/* ---------- tabs ---------- */
.stTabs [data-baseweb="tab-list"]{ gap:.4rem; background:rgba(14,21,48,.7); padding:.35rem; border-radius:14px; border:1px solid var(--stroke); }
.stTabs [data-baseweb="tab"]{ height:42px; border-radius:10px; padding:0 1rem; color:var(--muted) !important; font-weight:700; }
.stTabs [aria-selected="true"]{ background:linear-gradient(135deg,rgba(124,58,237,.55),rgba(6,182,212,.45)) !important; color:#fff !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"]{ display:none; }

/* ---------- containers ---------- */
[data-testid="stExpander"], [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {
  border-radius:16px !important;
}
[data-testid="stExpander"]{ background:var(--panel) !important; border:1px solid var(--stroke) !important; }
[data-testid="stExpander"] summary *{ color:var(--text) !important; font-weight:700; }
[data-testid="stChatMessage"]{ background:var(--panel) !important; border:1px solid var(--stroke); border-radius:16px; padding:.9rem 1rem;
  backdrop-filter: blur(10px); margin-bottom:.55rem; }
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li{ color:var(--text) !important; line-height:1.6; }
[data-testid="stDataFrame"]{ border-radius:12px; overflow:hidden; border:1px solid var(--stroke); }
.stAlert{ border-radius:14px !important; }
[data-testid="stMetric"]{ background:var(--panel); border:1px solid var(--stroke); border-radius:14px; padding:.8rem 1rem; }

/* ---------- custom components ---------- */
.hero{ position:relative; padding:1.6rem 1.8rem; border-radius:22px; margin-bottom:1.1rem; overflow:hidden;
  background:linear-gradient(135deg, rgba(124,58,237,.32), rgba(37,99,235,.18) 45%, rgba(6,182,212,.22));
  border:1px solid var(--stroke-strong); box-shadow:0 20px 60px rgba(8,12,30,.6); }
.hero::after{ content:""; position:absolute; right:-80px; top:-80px; width:280px; height:280px; border-radius:50%;
  background:radial-gradient(circle, rgba(34,211,238,.35), transparent 65%); }
.hero h1{ margin:0; font-size:2.1rem; font-weight:800; letter-spacing:-.5px; color:#fff; }
.hero h1 span{ background:linear-gradient(90deg,#C4B5FD,#67E8F9); -webkit-background-clip:text; background-clip:text; color:transparent; }
.hero p{ margin:.35rem 0 0; color:#D6DCF5; font-size:1.02rem; max-width:760px; }
.chip-row{ display:flex; flex-wrap:wrap; gap:.45rem; margin-top:.9rem; position:relative; z-index:1 }
.chip{ font-size:.76rem; font-weight:700; padding:.28rem .7rem; border-radius:999px; background:rgba(6,9,20,.55);
  border:1px solid var(--stroke-strong); color:#E0E7FF; }

.pipeline{ display:grid; grid-template-columns:repeat(6,1fr); gap:.5rem; margin:.4rem 0 1rem; }
.step{ position:relative; padding:.75rem .7rem; border-radius:14px; background:rgba(14,21,48,.75); border:1px solid var(--stroke);
  text-align:center; transition:all .25s; }
.step .ic{ font-size:1.25rem; } .step .nm{ font-weight:800; font-size:.86rem; color:var(--text); margin-top:.15rem }
.step .sub{ font-size:.7rem; color:var(--muted); }
.step.done{ border-color:rgba(52,211,153,.55); background:linear-gradient(180deg,rgba(52,211,153,.16),rgba(14,21,48,.8)); }
.step.active{ border-color:var(--cyan); box-shadow:0 0 0 3px rgba(34,211,238,.18), 0 0 26px rgba(34,211,238,.35); animation:pulse 1.4s infinite; }
.step.warn{ border-color:rgba(251,191,36,.7); background:linear-gradient(180deg,rgba(251,191,36,.16),rgba(14,21,48,.8)); }
.step .loop{ position:absolute; top:-8px; right:-6px; font-size:.68rem; font-weight:800; padding:.1rem .45rem; border-radius:999px;
  background:var(--amber); color:#1F1300; }
@keyframes pulse{ 0%,100%{ box-shadow:0 0 0 3px rgba(34,211,238,.18),0 0 16px rgba(34,211,238,.25)} 50%{ box-shadow:0 0 0 5px rgba(34,211,238,.28),0 0 34px rgba(34,211,238,.5)} }

.badge{ display:inline-flex; align-items:center; gap:.4rem; font-weight:800; font-size:.8rem; letter-spacing:.3px;
  padding:.18rem .65rem; border-radius:999px; margin-bottom:.35rem; }
.badge .tag{ font-weight:700; font-size:.68rem; padding:.05rem .45rem; border-radius:6px; background:rgba(0,0,0,.35); }

.answer-card{ border-radius:20px; padding:1.4rem 1.6rem; margin:.4rem 0 1rem;
  background:linear-gradient(160deg, rgba(16,185,129,.16), rgba(14,21,48,.88) 40%); border:1px solid rgba(52,211,153,.5);
  box-shadow:0 18px 50px rgba(16,185,129,.12); }
.answer-card h4{ margin:.2rem 0 .3rem; font-size:.74rem; letter-spacing:1.8px; text-transform:uppercase; color:var(--green); font-weight:800; }
.answer-card .big{ font-size:1.12rem; line-height:1.65; color:#F8FAFF; font-weight:500; }
.answer-card .src{ color:#D9E1FA; line-height:1.6; }
.next-q{ margin-top:.9rem; padding:.75rem 1rem; border-radius:12px; background:rgba(167,139,250,.12); border:1px dashed rgba(167,139,250,.6); color:#E9E3FF; }

.card{ padding:1.1rem 1.2rem; border-radius:16px; background:var(--panel); border:1px solid var(--stroke); height:100%; }
.card .n{ font-size:.72rem; font-weight:800; color:var(--cyan); letter-spacing:1.5px } .card b{ display:block; margin:.25rem 0; font-size:1.02rem; color:#fff }
.card p{ color:var(--muted); margin:0; font-size:.9rem }
.kpi{ padding:.85rem 1rem; border-radius:14px; background:var(--panel); border:1px solid var(--stroke); }
.kpi .l{ font-size:.7rem; color:var(--muted); font-weight:700; letter-spacing:1.2px; text-transform:uppercase }
.kpi .v{ font-size:1.45rem; font-weight:800; color:#fff; margin-top:.1rem }
.kpi .v small{ font-size:.8rem; color:var(--muted); font-weight:600 }
.status-pill{ display:inline-block; padding:.25rem .7rem; border-radius:999px; font-weight:800; font-size:.78rem; }
.st-ok{ background:rgba(52,211,153,.18); color:#6EE7B7; border:1px solid rgba(52,211,153,.5) }
.st-run{ background:rgba(34,211,238,.16); color:#67E8F9; border:1px solid rgba(34,211,238,.5) }
.st-warn{ background:rgba(251,191,36,.16); color:#FCD34D; border:1px solid rgba(251,191,36,.5) }
.st-idle{ background:rgba(148,163,255,.12); color:#C7D2FE; border:1px solid var(--stroke-strong) }
.run-sep{ display:flex; align-items:center; gap:.7rem; margin:1.1rem 0 .7rem; color:var(--muted); font-weight:800; font-size:.78rem; letter-spacing:1.4px; text-transform:uppercase }
.run-sep::before, .run-sep::after{ content:""; flex:1; height:1px; background:var(--stroke-strong) }

@media (max-width: 900px){ .pipeline{ grid-template-columns:repeat(3,1fr);} .hero h1{font-size:1.6rem} }
</style>
"""


def badge(source: str, tag: str | None = None) -> str:
    _, label, color = AGENT_STYLE.get(source, ("🤖", source, "#94A3B8"))
    t = f'<span class="tag">{html.escape(tag)}</span>' if tag else ""
    return (
        f'<span class="badge" style="background:{color}22;color:{color};border:1px solid {color}88">'
        f"{html.escape(label)}{t}</span>"
    )


STEPS = [("📥", "Ask", "Upload + question"), ("🧭", "Plan", "Planner"), ("🛠️", "Code", "Coder"),
         ("⚙️", "Run", "Executor"), ("🔍", "Review", "Reviewer"), ("✅", "Answer", "Human approves")]


def pipeline_html(state: dict) -> str:
    """state: {'done': set[int], 'active': int|None, 'warn': set[int], 'loops': {idx: n}}"""
    cells = []
    for i, (ic, nm, sub) in enumerate(STEPS):
        cls = "step"
        if i in state.get("warn", set()):
            cls += " warn"
        elif i == state.get("active"):
            cls += " active"
        elif i in state.get("done", set()):
            cls += " done"
        loop = state.get("loops", {}).get(i)
        loop_html = f'<span class="loop">↺ {loop}</span>' if loop else ""
        cells.append(f'<div class="{cls}">{loop_html}<div class="ic">{ic}</div><div class="nm">{nm}</div><div class="sub">{sub}</div></div>')
    return f'<div class="pipeline">{"".join(cells)}</div>'


def kpi(label: str, value: str, sub: str = "") -> str:
    s = f" <small>{html.escape(sub)}</small>" if sub else ""
    return f'<div class="kpi"><div class="l">{html.escape(label)}</div><div class="v">{html.escape(value)}{s}</div></div>'
