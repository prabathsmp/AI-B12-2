"""Custom visual theme + HTML components for the Streamlit UI."""
from __future__ import annotations

import html

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

:root{
  --bg:#06071a; --panel:rgba(20,22,52,.55); --panel-strong:rgba(26,28,66,.78);
  --border:rgba(160,150,255,.18); --text:#eef0ff; --muted:#a3a8d6;
  --violet:#7c5cff; --cyan:#22d3ee; --pink:#f472b6; --lime:#a3e635; --amber:#fbbf24;
}
html, body, [data-testid="stAppViewContainer"]{ background:var(--bg)!important; color:var(--text); }
[data-testid="stAppViewContainer"]{
  font-family:'Plus Jakarta Sans',sans-serif;
  background:
    radial-gradient(900px 600px at 8% -10%, rgba(124,92,255,.35), transparent 60%),
    radial-gradient(700px 500px at 100% 0%, rgba(34,211,238,.22), transparent 60%),
    radial-gradient(800px 600px at 60% 110%, rgba(244,114,182,.18), transparent 60%),
    var(--bg)!important;
}
[data-testid="stAppViewContainer"]::before{
  content:""; position:fixed; inset:-20%; pointer-events:none; z-index:0;
  background:
    radial-gradient(400px 300px at 20% 30%, rgba(124,92,255,.18), transparent 70%),
    radial-gradient(350px 260px at 80% 60%, rgba(34,211,238,.14), transparent 70%);
  animation: drift 22s ease-in-out infinite alternate; filter: blur(10px);
}
[data-testid="stAppViewContainer"]::after{
  content:""; position:fixed; inset:0; pointer-events:none; z-index:0; opacity:.35;
  background-image: linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: radial-gradient(ellipse at 50% 0%, #000 30%, transparent 75%);
}
@keyframes drift{ 0%{transform:translate(0,0) rotate(0)} 100%{transform:translate(6%,4%) rotate(8deg)} }
[data-testid="stHeader"]{ background:transparent!important; }
[data-testid="stMainBlockContainer"], .block-container{ position:relative; z-index:1; padding-top:2.2rem; max-width:1280px; }
h1,h2,h3,h4{ font-family:'Space Grotesk',sans-serif!important; color:var(--text)!important; letter-spacing:-.01em; }
p, li, label, span, div{ color:inherit; }

/* Sidebar */
[data-testid="stSidebar"]{ background:linear-gradient(180deg, rgba(14,15,40,.96), rgba(10,10,30,.96))!important; border-right:1px solid var(--border); }
[data-testid="stSidebar"] *{ color:var(--text); }

/* Inputs */
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea, [data-baseweb="select"] > div{
  background:rgba(10,12,34,.75)!important; color:var(--text)!important;
  border:1px solid var(--border)!important; border-radius:12px!important;
}
[data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus{
  border-color:var(--violet)!important; box-shadow:0 0 0 3px rgba(124,92,255,.25)!important;
}
[data-testid="stWidgetLabel"] p{ color:var(--muted)!important; font-weight:600; font-size:.86rem; letter-spacing:.02em; }

/* Form card */
[data-testid="stForm"]{
  background:var(--panel); border:1px solid var(--border)!important; border-radius:22px!important;
  padding:1.4rem 1.4rem .6rem!important; backdrop-filter:blur(14px);
  box-shadow:0 20px 60px -20px rgba(0,0,0,.6), inset 0 1px 0 rgba(255,255,255,.05);
}

/* Buttons */
.stButton button, [data-testid="stFormSubmitButton"] button, [data-testid="stDownloadButton"] button{
  border-radius:14px!important; font-weight:700!important; border:1px solid var(--border)!important;
  background:rgba(124,92,255,.12)!important; color:var(--text)!important; transition:all .2s ease;
}
.stButton button:hover, [data-testid="stDownloadButton"] button:hover{ border-color:var(--violet)!important; transform:translateY(-1px); }
[data-testid="stFormSubmitButton"] button{
  background:linear-gradient(135deg,#7c5cff 0%,#4f7bff 50%,#22d3ee 100%)!important; border:0!important;
  padding:.75rem 1.2rem!important; font-size:1.02rem!important; color:#fff!important;
  box-shadow:0 12px 30px -10px rgba(124,92,255,.8);
}
[data-testid="stFormSubmitButton"] button:hover{ filter:brightness(1.1); transform:translateY(-2px); }

/* Sample pills */
[data-testid="stButtonGroup"] > div{ flex-wrap:wrap!important; overflow:visible!important; }
[data-testid="stButtonGroup"] button{ background:rgba(255,255,255,.05)!important; border:1px solid var(--border)!important; color:#dfe2ff!important; border-radius:999px!important; }
[data-testid="stButtonGroup"] button:hover{ border-color:var(--violet)!important; background:rgba(124,92,255,.18)!important; }

/* Tabs */
[data-baseweb="tab-list"]{ gap:.4rem; background:rgba(10,12,34,.5); padding:.35rem; border-radius:14px; border:1px solid var(--border); }
[data-baseweb="tab"]{ border-radius:10px!important; padding:.45rem 1rem!important; color:var(--muted)!important; }
[data-baseweb="tab"][aria-selected="true"]{ background:linear-gradient(135deg,rgba(124,92,255,.45),rgba(34,211,238,.25))!important; color:#fff!important; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"]{ display:none; }

[data-testid="stExpander"]{ background:var(--panel); border:1px solid var(--border)!important; border-radius:16px!important; }
[data-testid="stAlert"]{ border-radius:14px; }

/* ---------- custom components ---------- */
.hero{ position:relative; padding:2.2rem 2.2rem 2rem; border-radius:28px; overflow:hidden; margin-bottom:1.4rem;
  background:linear-gradient(135deg, rgba(124,92,255,.22), rgba(34,211,238,.10) 55%, rgba(244,114,182,.14));
  border:1px solid var(--border); box-shadow:0 30px 80px -30px rgba(124,92,255,.55); }
.hero::after{ content:""; position:absolute; right:-80px; top:-80px; width:320px; height:320px; border-radius:50%;
  background:conic-gradient(from 0deg, #7c5cff, #22d3ee, #f472b6, #7c5cff); filter:blur(60px); opacity:.45;
  animation:spin 14s linear infinite; }
@keyframes spin{ to{ transform:rotate(360deg) } }
.hero .eyebrow{ display:inline-flex; gap:.5rem; align-items:center; font-size:.78rem; font-weight:700; letter-spacing:.14em;
  text-transform:uppercase; color:#cfc6ff; background:rgba(124,92,255,.18); border:1px solid rgba(124,92,255,.4);
  padding:.35rem .8rem; border-radius:999px; }
.hero h1{ font-size:3rem!important; line-height:1.05; margin:.9rem 0 .6rem!important; position:relative; z-index:1; }
.grad{ background:linear-gradient(90deg,#b9a8ff,#7cc8ff 45%,#ff9ad5); -webkit-background-clip:text; background-clip:text; color:transparent!important; }
.hero p.sub{ color:var(--muted); font-size:1.08rem; max-width:760px; position:relative; z-index:1; margin:0; }
.chips{ display:flex; flex-wrap:wrap; gap:.5rem; margin-top:1.2rem; position:relative; z-index:1; }
.chip{ font-size:.8rem; padding:.35rem .75rem; border-radius:999px; background:rgba(255,255,255,.06); border:1px solid var(--border); color:#dfe2ff; }

.section-title{ font-family:'Space Grotesk',sans-serif; font-size:1.15rem; font-weight:700; margin:.4rem 0 .8rem; display:flex; align-items:center; gap:.55rem; }
.section-title .dot{ width:10px; height:10px; border-radius:50%; background:linear-gradient(135deg,var(--violet),var(--cyan)); box-shadow:0 0 12px var(--violet); }

.pipeline{ display:grid; grid-template-columns:repeat(6,1fr); gap:.6rem; margin:.2rem 0 1.4rem; }
.pipe{ background:var(--panel); border:1px solid var(--border); border-radius:16px; padding:.8rem .8rem; text-align:left; }
.pipe .n{ font-family:'Space Grotesk'; font-weight:700; font-size:.78rem; color:var(--cyan); letter-spacing:.1em; }
.pipe .t{ font-weight:700; font-size:.95rem; margin-top:.15rem; }
.pipe .d{ color:var(--muted); font-size:.76rem; margin-top:.2rem; line-height:1.3; }

.agents{ display:grid; grid-template-columns:repeat(2,1fr); gap:.9rem; }
.agent{ position:relative; background:var(--panel); border:1px solid var(--border); border-radius:20px; padding:1.1rem; overflow:hidden;
  backdrop-filter:blur(12px); transition:all .3s ease; min-height:150px; }
.agent .hd{ display:flex; justify-content:space-between; align-items:flex-start; gap:.5rem; }
.agent .ic{ width:46px; height:46px; border-radius:14px; display:grid; place-items:center; font-size:1.4rem;
  background:linear-gradient(135deg,rgba(124,92,255,.35),rgba(34,211,238,.2)); border:1px solid var(--border); }
.agent .nm{ font-family:'Space Grotesk'; font-weight:700; font-size:1.02rem; margin-top:.7rem; }
.agent .bl{ color:var(--muted); font-size:.8rem; margin-top:.2rem; line-height:1.35; }
.agent .st{ position:relative; z-index:1; font-size:.7rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase;
  padding:.25rem .55rem; border-radius:999px; border:1px solid var(--border); color:var(--muted); background:rgba(255,255,255,.04); }
.agent .meta{ margin-top:.6rem; font-size:.75rem; color:#c9ccf5; }
.agent.working{ border-color:rgba(34,211,238,.7); box-shadow:0 0 0 1px rgba(34,211,238,.4), 0 18px 50px -18px rgba(34,211,238,.7); }
.agent.working::before{ content:""; position:absolute; inset:0; background:linear-gradient(110deg,transparent 30%,rgba(34,211,238,.16) 50%,transparent 70%);
  background-size:250% 100%; animation:shimmer 1.8s linear infinite; }
.agent.working .st{ color:#06071a; background:var(--cyan); border-color:var(--cyan); animation:pulse 1.2s ease-in-out infinite; }
.agent.done{ border-color:rgba(163,230,53,.45); }
.agent.done .st{ color:#0b1400; background:var(--lime); border-color:var(--lime); }
.agent.error .st{ color:#fff; background:#ef4444; border-color:#ef4444; }
@keyframes shimmer{ 0%{background-position:200% 0} 100%{background-position:-50% 0} }
@keyframes pulse{ 50%{ opacity:.55 } }
.bar{ height:6px; border-radius:99px; background:rgba(255,255,255,.07); overflow:hidden; margin:1rem 0 .3rem; }
.bar > i{ display:block; height:100%; background:linear-gradient(90deg,var(--violet),var(--cyan),var(--pink)); border-radius:99px; transition:width .6s ease; }

.log{ background:rgba(8,9,26,.72); border:1px solid var(--border); border-radius:18px; padding:.9rem 1rem; max-height:420px; overflow-y:auto;
  font-size:.84rem; }
.log .row{ display:grid; grid-template-columns:62px 26px 1fr; gap:.5rem; padding:.5rem 0; border-bottom:1px dashed rgba(160,150,255,.12); }
.log .row:last-child{ border-bottom:0; }
.log .tm{ color:#7d82b8; font-family:'Space Grotesk'; font-size:.78rem; padding-top:.1rem; }
.log .who{ font-weight:700; color:#d8d2ff; }
.log .tool{ display:inline-block; font-size:.7rem; padding:.05rem .45rem; border-radius:6px; background:rgba(34,211,238,.14); color:#8be9fb;
  border:1px solid rgba(34,211,238,.3); margin-left:.35rem; }
.log .txt{ color:#b7bbe6; margin-top:.15rem; word-break:break-word; }
.log .empty{ color:var(--muted); text-align:center; padding:1.6rem; }

.stats{ display:grid; grid-template-columns:repeat(4,1fr); gap:.8rem; margin:.4rem 0 1.1rem; }
.stat{ background:var(--panel); border:1px solid var(--border); border-radius:18px; padding:1rem 1.1rem; }
.stat .k{ color:var(--muted); font-size:.75rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; }
.stat .v{ font-family:'Space Grotesk'; font-size:1.7rem; font-weight:700; margin-top:.2rem; }

.st-key-report{ background:linear-gradient(180deg, rgba(22,24,58,.82), rgba(14,15,40,.82)); border:1px solid var(--border); border-radius:22px;
  padding:1.6rem 1.9rem; box-shadow:0 30px 80px -40px rgba(0,0,0,.8); }
.st-key-report table{ width:100%; border-collapse:separate; border-spacing:0; overflow:hidden; border-radius:12px; border:1px solid var(--border); }
.st-key-report th{ background:rgba(124,92,255,.22); color:#fff; text-align:left; padding:.6rem .7rem; font-size:.86rem; }
.st-key-report td{ padding:.55rem .7rem; border-top:1px solid rgba(160,150,255,.12); font-size:.88rem; color:#dadcf7; }
.st-key-report tr:nth-child(even) td{ background:rgba(255,255,255,.02); }
.st-key-report blockquote{ border-left:4px solid var(--violet); background:rgba(124,92,255,.12); margin:.6rem 0; padding:.6rem 1rem; border-radius:0 12px 12px 0; }
.st-key-report a{ color:#8cc8ff; }
.st-key-report h1{ font-size:2rem!important; line-height:1.15; }
.st-key-report h2{ margin-top:1.4rem!important; padding-bottom:.35rem; border-bottom:1px solid var(--border); }

.empty-state{ text-align:center; padding:2.6rem 1rem; border:1px dashed var(--border); border-radius:22px; background:rgba(255,255,255,.02); color:var(--muted); }
.empty-state .big{ font-size:2.4rem; }
.pill{ display:inline-block; padding:.2rem .6rem; border-radius:999px; font-size:.75rem; font-weight:700; border:1px solid var(--border); }
.pill.ok{ background:rgba(163,230,53,.14); color:#c5f27a; border-color:rgba(163,230,53,.4); }
.pill.warn{ background:rgba(251,191,36,.14); color:#fcd34d; border-color:rgba(251,191,36,.4); }
.footer{ color:#6e73a6; text-align:center; font-size:.8rem; margin:2.4rem 0 1rem; }

@media (max-width: 1000px){ .stats{ grid-template-columns:repeat(2,1fr);} .pipeline{ grid-template-columns:repeat(3,1fr);} .hero h1{ font-size:2.2rem!important; } }
@media (max-width: 560px){ .agents, .stats{ grid-template-columns:1fr;} .pipeline{ grid-template-columns:repeat(2,1fr);} }
</style>
"""

PIPELINE = [
    ("01", "Idea input", "Founder fills the form"),
    ("02", "Research", "Competitors & prices"),
    ("03", "Reviews", "Customer pain points"),
    ("04", "Strategy", "Matrix, gap, price"),
    ("05", "Write", "Founder-ready report"),
    ("06", "Deliver", "View & download"),
]

STATUS_LABEL = {"waiting": "Waiting", "working": "Working", "done": "Done", "error": "Error"}


def esc(text) -> str:
    return html.escape(str(text or ""))


def hero(search_provider: str, model: str) -> str:
    return f"""
<div class="hero">
  <span class="eyebrow">✦ AI Agents · CrewAI · 4-agent crew</span>
  <h1>Launch<span class="grad">Scout</span></h1>
  <p class="sub">Drop in a business idea and a city. Four specialised AI agents research real competitors,
  read their reviews, find the market gap and hand you a sourced launch report, in minutes, not days.</p>
  <div class="chips">
    <span class="chip">🧠 Model: {esc(model)}</span>
    <span class="chip">🌐 Search: {esc(search_provider)}</span>
    <span class="chip">📄 Markdown + PDF export</span>
    <span class="chip">🔗 Every claim sourced</span>
  </div>
</div>"""


def pipeline() -> str:
    cells = "".join(
        f'<div class="pipe"><div class="n">{n}</div><div class="t">{t}</div><div class="d">{d}</div></div>'
        for n, t, d in PIPELINE
    )
    return f'<div class="pipeline">{cells}</div>'


def section_title(text: str) -> str:
    return f'<div class="section-title"><span class="dot"></span>{esc(text)}</div>'


def agent_cards(agents: list[dict], status: dict, counts: dict) -> str:
    done = sum(1 for a in agents if status.get(a["key"]) == "done")
    working = any(status.get(a["key"]) == "working" for a in agents)
    pct = int((done + (0.5 if working else 0)) / len(agents) * 100)
    cards = []
    for a in agents:
        st = status.get(a["key"], "waiting")
        n = counts.get(a["key"], 0)
        meta = f"{n} action{'s' if n != 1 else ''}" if n else "—"
        cards.append(
            f'<div class="agent {st}"><div class="hd"><div class="ic">{a["icon"]}</div>'
            f'<span class="st">{STATUS_LABEL.get(st, st)}</span></div><div class="nm">{esc(a["name"])}</div>'
            f'<div class="bl">{esc(a["blurb"])}</div><div class="meta">⚡ {meta}</div></div>'
        )
    return f'<div class="agents">{"".join(cards)}</div><div class="bar"><i style="width:{pct}%"></i></div>'


def activity_log(rows: list[dict], names: dict) -> str:
    if not rows:
        return '<div class="log"><div class="empty">Agent activity will stream here once the crew starts.</div></div>'
    items = []
    for r in reversed(rows[-60:]):
        tool = f'<span class="tool">{esc(r.get("tool"))}</span>' if r.get("tool") else ""
        items.append(
            f'<div class="row"><div class="tm">{esc(r["time"])}</div><div>{r.get("icon", "•")}</div>'
            f'<div><span class="who">{esc(names.get(r.get("agent"), r.get("agent", "Crew")))}</span>{tool}'
            f'<div class="txt">{esc(r.get("text"))}</div></div></div>'
        )
    return f'<div class="log">{"".join(items)}</div>'


def stats(items: list[tuple[str, str]]) -> str:
    cells = "".join(f'<div class="stat"><div class="k">{esc(k)}</div><div class="v">{esc(v)}</div></div>' for k, v in items)
    return f'<div class="stats">{cells}</div>'


def empty_state() -> str:
    return """<div class="empty-state"><div class="big">🛰️</div>
<div style="font-weight:700;color:#e6e8ff;margin:.4rem 0 .2rem">Your report will land here</div>
<div>Fill in the brief and press <b>Launch the crew</b>.</div></div>"""
