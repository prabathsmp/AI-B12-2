"""Presentation helpers: theme CSS, hero banner, workflow stepper, feature cards.

Pure UI - no business logic here. Keyed containers (key="card_*") are styled as cards via the
`st-key-card_*` class Streamlit adds to them.
"""
from __future__ import annotations

import html

import streamlit as st

BRAND = "#4f46e5"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --rl-primary: #4f46e5;
  --rl-primary-2: #7c3aed;
  --rl-accent: #06b6d4;
  --rl-ink: #1e1b4b;
  --rl-muted: #64748b;
  --rl-card: rgba(255,255,255,0.86);
  --rl-border: rgba(79,70,229,0.12);
  --rl-shadow: 0 10px 30px -12px rgba(30,27,75,0.18), 0 2px 6px -2px rgba(30,27,75,0.06);
}

html, body, [class*="css"], .stApp, button, input, textarea, select {
  font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif !important;
}

/* ---------- page background ---------- */
.stApp {
  background:
    radial-gradient(1200px 600px at 0% -10%, rgba(124,58,237,0.13), transparent 60%),
    radial-gradient(900px 500px at 100% 0%, rgba(6,182,212,0.12), transparent 55%),
    radial-gradient(800px 600px at 50% 110%, rgba(79,70,229,0.08), transparent 60%),
    linear-gradient(180deg, #f8f9ff 0%, #f3f4fb 100%);
  background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1320px; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #ffffff 0%, #f5f3ff 100%);
  border-right: 1px solid var(--rl-border);
}
.rl-brand { display:flex; align-items:center; gap:.6rem; margin:.2rem 0 1rem; }
.rl-brand .logo {
  width:38px; height:38px; border-radius:11px; display:grid; place-items:center; font-size:1.2rem;
  background: linear-gradient(135deg, var(--rl-primary), var(--rl-primary-2)); color:#fff;
  box-shadow: 0 6px 16px -6px rgba(79,70,229,.6);
}
.rl-brand .name { font-weight:800; font-size:1.15rem; color:var(--rl-ink); line-height:1.1; }
.rl-brand .sub { font-size:.72rem; color:var(--rl-muted); }
.rl-side-label { font-size:.7rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase;
  color:var(--rl-muted); margin:.4rem 0 .2rem; }

/* ---------- hero ---------- */
.rl-hero {
  position:relative; overflow:hidden; border-radius:22px; padding:2.1rem 2.3rem 1.9rem;
  background: linear-gradient(120deg, #312e81 0%, #4f46e5 38%, #7c3aed 70%, #0891b2 100%);
  color:#fff; box-shadow: 0 24px 50px -24px rgba(49,46,129,.65); margin-bottom:1.3rem;
}
.rl-hero::before, .rl-hero::after {
  content:""; position:absolute; border-radius:50%; filter:blur(2px); opacity:.35;
}
.rl-hero::before { width:340px; height:340px; right:-80px; top:-140px;
  background: radial-gradient(circle, rgba(255,255,255,.55), transparent 65%); }
.rl-hero::after { width:260px; height:260px; left:40%; bottom:-170px;
  background: radial-gradient(circle, rgba(34,211,238,.7), transparent 65%); }
.rl-hero .eyebrow { font-size:.75rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase;
  opacity:.85; }
.rl-hero h1 { font-size:2.6rem; font-weight:800; margin:.25rem 0 .35rem; color:#fff; letter-spacing:-.02em;
  padding:0; }
.rl-hero p.tag { font-size:1.06rem; max-width:760px; opacity:.93; margin:0 0 1rem; line-height:1.55; }
.rl-pills { display:flex; flex-wrap:wrap; gap:.45rem; position:relative; z-index:1; }
.rl-pill { font-size:.78rem; font-weight:600; padding:.32rem .75rem; border-radius:999px;
  background: rgba(255,255,255,.16); border:1px solid rgba(255,255,255,.28); backdrop-filter: blur(6px); }

/* ---------- stepper ---------- */
.rl-steps { display:grid; grid-template-columns: repeat(6, minmax(0,1fr)); gap:.55rem; margin: .2rem 0 1.4rem; }
.rl-step { background:var(--rl-card); border:1px solid var(--rl-border); border-radius:14px;
  padding:.65rem .75rem; display:flex; gap:.6rem; align-items:center; box-shadow: var(--rl-shadow);
  transition: all .2s ease; }
.rl-step .n { flex:0 0 28px; height:28px; border-radius:9px; display:grid; place-items:center;
  font-size:.8rem; font-weight:800; background:#eef2ff; color:var(--rl-primary); }
.rl-step .t { font-size:.82rem; font-weight:700; color:var(--rl-ink); line-height:1.15; }
.rl-step .d { font-size:.7rem; color:var(--rl-muted); line-height:1.2; }
.rl-step.done .n { background:#dcfce7; color:#15803d; }
.rl-step.active { border-color: rgba(79,70,229,.55); box-shadow: 0 0 0 3px rgba(79,70,229,.12), var(--rl-shadow); }
.rl-step.active .n { background: linear-gradient(135deg, var(--rl-primary), var(--rl-primary-2)); color:#fff; }
@media (max-width: 1100px) { .rl-steps { grid-template-columns: repeat(3, minmax(0,1fr)); } }
@media (max-width: 640px)  { .rl-steps { grid-template-columns: repeat(2, minmax(0,1fr)); }
  .rl-hero h1 { font-size:2rem; } .rl-hero { padding:1.5rem; } }

/* ---------- section titles ---------- */
.rl-section { display:flex; align-items:center; gap:.65rem; margin: 1.2rem 0 .6rem; }
.rl-section .badge { width:30px; height:30px; border-radius:10px; display:grid; place-items:center;
  background: linear-gradient(135deg, var(--rl-primary), var(--rl-primary-2)); color:#fff; font-weight:800;
  font-size:.85rem; box-shadow: 0 6px 14px -6px rgba(79,70,229,.6); }
.rl-section .title { font-size:1.22rem; font-weight:800; color:var(--rl-ink); letter-spacing:-.01em; }
.rl-section .hint { font-size:.85rem; color:var(--rl-muted); margin-left:.2rem; }
@media (max-width: 640px) { .rl-section { flex-wrap:wrap; row-gap:.2rem; }
  .rl-section .hint { flex-basis:100%; margin-left:2.6rem; } }

/* ---------- cards (keyed containers + metrics) ---------- */
[class*="st-key-card"] {
  background: var(--rl-card); border:1px solid var(--rl-border) !important; border-radius:18px !important;
  padding: 1.1rem 1.2rem; box-shadow: var(--rl-shadow); backdrop-filter: blur(8px);
}
[data-testid="stMetric"] {
  background: var(--rl-card); border:1px solid var(--rl-border); border-radius:16px;
  padding: .9rem 1.1rem; box-shadow: var(--rl-shadow);
}
[data-testid="stMetricLabel"] p { font-weight:600; color: var(--rl-muted); font-size:.82rem; }
[data-testid="stMetricValue"] { font-weight:800; color: var(--rl-ink); }

/* ---------- feature cards ---------- */
.rl-features { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:1rem; margin:.4rem 0 1rem; }
.rl-feature { background:var(--rl-card); border:1px solid var(--rl-border); border-radius:18px;
  padding:1.2rem 1.25rem; box-shadow:var(--rl-shadow); }
.rl-feature .ic { width:42px; height:42px; border-radius:12px; display:grid; place-items:center;
  font-size:1.25rem; margin-bottom:.7rem; }
.rl-feature h4 { margin:0 0 .3rem; font-size:1rem; font-weight:700; color:var(--rl-ink); padding:0; }
.rl-feature p { margin:0; font-size:.86rem; color:var(--rl-muted); line-height:1.5; }
@media (max-width: 900px) { .rl-features { grid-template-columns: 1fr; } }

.rl-format { font-family: ui-monospace, 'SFMono-Regular', Consolas, monospace; font-size:.8rem;
  background:#1e1b4b; color:#e0e7ff; border-radius:12px; padding:.8rem 1rem; overflow-x:auto;
  white-space:pre; line-height:1.55; }
.rl-format .h { color:#a5b4fc; font-weight:700; }

/* ---------- widgets ---------- */
[data-testid="stFileUploaderDropzone"] {
  background: linear-gradient(135deg, rgba(238,242,255,.9), rgba(245,243,255,.9));
  border: 2px dashed rgba(79,70,229,.35); border-radius:14px;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--rl-primary); }
.stButton > button, .stDownloadButton > button {
  border-radius: 11px; font-weight:600; transition: transform .12s ease, box-shadow .12s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-1px); }
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--rl-primary), var(--rl-primary-2)); border:0;
  box-shadow: 0 10px 22px -10px rgba(79,70,229,.8);
}
.stTabs [data-baseweb="tab-list"] { gap:.35rem; background: rgba(255,255,255,.6); padding:.35rem;
  border-radius:14px; border:1px solid var(--rl-border); }
.stTabs [data-baseweb="tab"] { border-radius:10px; padding:.45rem .9rem; font-weight:600; height:auto; }
.stTabs [aria-selected="true"] { background:#fff; box-shadow: 0 2px 8px -2px rgba(30,27,75,.15); }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display:none; }
[data-testid="stExpander"] details { border-radius:14px; border:1px solid var(--rl-border);
  background: var(--rl-card); }
[data-testid="stDataFrame"] { border-radius:12px; overflow:hidden; }
[data-testid="stAlert"] { border-radius:12px; }

.rl-footer { text-align:center; color:var(--rl-muted); font-size:.78rem; margin-top:2.5rem; }
</style>
"""

STEPS = [
    ("Upload", "Weekly CSV"),
    ("Validate", "Columns & rows"),
    ("Classify", "LLM, batched"),
    ("Aggregate", "pandas counts"),
    ("Report", "Weekly insights"),
    ("Export", "Dashboard & CSV"),
]


def inject_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def sidebar_brand(version: str) -> None:
    st.markdown(
        f"""<div class="rl-brand"><div class="logo">🔎</div>
        <div><div class="name">ReviewLens</div><div class="sub">Feedback Analyzer · v{html.escape(version)}</div></div>
        </div>""", unsafe_allow_html=True)


def side_label(text: str) -> None:
    st.markdown(f'<div class="rl-side-label">{html.escape(text)}</div>', unsafe_allow_html=True)


def hero(model: str) -> None:
    pills = ["🌐 English · Tamil · Tanglish", "🧠 " + model, "🧩 Structured LLM output",
             "⚡ Batched & auto-retry", "📊 Numbers from pandas"]
    st.markdown(
        f"""<div class="rl-hero">
          <div class="eyebrow">Gen AI · LangChain · Customer Feedback Analyzer</div>
          <h1>ReviewLens</h1>
          <p class="tag">Turn hundreds of raw customer reviews from Google, Zomato, Swiggy and Amazon into
          tagged, prioritised insights and a weekly report a manager can act on in <b>five minutes</b>.</p>
          <div class="rl-pills">{''.join(f'<span class="rl-pill">{html.escape(p)}</span>' for p in pills)}</div>
        </div>""", unsafe_allow_html=True)


def stepper_html(active: int) -> str:
    """active: 1-based index of the current step; steps before it are shown as done."""
    items = []
    for i, (t, d) in enumerate(STEPS, 1):
        cls = "done" if i < active else ("active" if i == active else "")
        num = "✓" if i < active else f"{i:02d}"
        items.append(f'<div class="rl-step {cls}"><div class="n">{num}</div>'
                     f'<div><div class="t">{t}</div><div class="d">{d}</div></div></div>')
    return f'<div class="rl-steps">{"".join(items)}</div>'


def section(num: str, title: str, hint: str = "") -> None:
    h = f'<span class="hint">{html.escape(hint)}</span>' if hint else ""
    st.markdown(f'<div class="rl-section"><div class="badge">{html.escape(num)}</div>'
                f'<div class="title">{html.escape(title)}</div>{h}</div>', unsafe_allow_html=True)


def landing_features() -> None:
    cards = [
        ("🏷️", "#eef2ff", "Tag every review",
         "Sentiment, category, urgency, language, a one-line English summary and a polite ready-to-post reply."),
        ("🚨", "#fef2f2", "Never miss an urgent one",
         "Food safety, wrong orders, refunds and rude staff are flagged HIGH so the team replies today."),
        ("📝", "#ecfeff", "Weekly report in 5 minutes",
         "Top complaints, top praise and 3 action items, with every number calculated exactly in pandas."),
    ]
    st.markdown('<div class="rl-features">' + "".join(
        f'<div class="rl-feature"><div class="ic" style="background:{bg}">{ic}</div>'
        f'<h4>{html.escape(t)}</h4><p>{html.escape(d)}</p></div>' for ic, bg, t, d in cards) + "</div>",
        unsafe_allow_html=True)
    st.markdown(
        '<div class="rl-format"><span class="h">review_id,date,platform,rating,review_text</span>\n'
        'R-1041,2026-10-03,Zomato,5,"Biryani was amazing, packing also neat. Will order again!"\n'
        'R-1042,2026-10-03,Swiggy,1,"Ordered at 8pm, came at 9:10. Food fully cold. Very bad."\n'
        'R-1043,2026-10-04,Google,2,"Saapadu nalla irundhuchu but bill la extra charge pottanga"</div>',
        unsafe_allow_html=True)


def footer(version: str) -> None:
    st.markdown(f'<div class="rl-footer">ReviewLens v{html.escape(version)} · counts computed in pandas, '
                f'text by LLM · your API key never leaves this session</div>', unsafe_allow_html=True)


def style_fig(fig, height: int = 320):
    """Transparent Plotly background + Inter font so charts sit nicely inside cards."""
    fig.update_layout(
        template="plotly_white", height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color="#1e1b4b"),
        title=dict(font=dict(size=15, color="#1e1b4b"), x=0.01),
        margin=dict(t=48, b=10, l=10, r=10), legend_title=None,
    )
    fig.update_xaxes(gridcolor="rgba(30,27,75,0.06)")
    fig.update_yaxes(gridcolor="rgba(30,27,75,0.06)")
    return fig
