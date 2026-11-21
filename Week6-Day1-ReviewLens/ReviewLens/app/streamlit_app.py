"""ReviewLens - Streamlit UI.

Workflow: 01 Upload -> 02 Validate -> 03 Classify -> 04 Aggregate -> 05 Report -> 06 Show + Export
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from reviewlens import __version__, ui
from reviewlens.aggregate import arrow, compute_stats, counts, ok_rows, trend
from reviewlens.classifier import classify_reviews, retry_needs_review
from reviewlens.config import (CATEGORIES, LANGUAGES, MODEL_CHOICES, SENTIMENTS, STATUS_NEEDS_REVIEW,
                               URGENCIES, settings)
from reviewlens.export import load_enriched, to_excel_csv
from reviewlens.llm import MissingAPIKeyError, check_key, get_llm
from reviewlens.report import build_weekly_report, generate_insights, render_report
from reviewlens.validation import CSVValidationError, validate_reviews

SAMPLE = Path(__file__).parent / "sample_data" / "reviews_week40.csv"
SENT_COLORS = {"positive": "#16a34a", "neutral": "#94a3b8", "negative": "#e11d48"}
URG_COLORS = {"low": "#94a3b8", "medium": "#f59e0b", "high": "#e11d48"}
PLOT_CFG = {"displayModeBar": False}

st.set_page_config(page_title="ReviewLens · Customer Feedback Analyzer", page_icon="🔎", layout="wide")
ui.inject_theme()

ss = st.session_state
for k, v in dict(raw=None, vreport=None, src_sig=None, enriched=None, stats=None, insights=None,
                 report=None, prev_df=None, prev_stats=None, run_secs=None).items():
    ss.setdefault(k, v)


def reset_results():
    for k in ("enriched", "stats", "insights", "report", "run_secs"):
        ss[k] = None


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    ui.sidebar_brand(__version__)
    ui.side_label("OpenAI connection")
    env_key = bool(settings.openai_api_key)
    ui_key = st.text_input(
        "OpenAI API key", type="password",
        placeholder="Using key from .env" if env_key else "sk-...",
        help="Kept only in this browser session's memory, never written to disk. "
             "Leave blank to use OPENAI_API_KEY from .env.")
    api_key = ui_key.strip() or settings.openai_api_key
    if ui_key.strip():
        st.caption("🔑 Using the key entered above (this session only).")
    elif env_key:
        st.caption("🔑 Using OPENAI_API_KEY from .env.")
    else:
        st.warning("No API key yet. Paste one above or set OPENAI_API_KEY in .env.")

    models = list(dict.fromkeys([settings.openai_model] + MODEL_CHOICES))
    model = st.selectbox("Model", models, index=0)
    custom = st.text_input("…or custom model id", placeholder="e.g. gpt-4.1-nano")
    model = custom.strip() or model

    if st.button("Test API key", width="stretch"):
        with st.spinner("Calling OpenAI…"):
            ok, msg = check_key(api_key, model)
        (st.success if ok else st.error)(msg)

    st.divider()
    ui.side_label("Processing")
    concurrency = st.slider("Batch concurrency", 1, 20, settings.max_concurrency,
                            help="Parallel LLM calls (chain.batch max_concurrency). Lower it if you hit rate limits.")
    reply_mode = st.radio("Suggested reply language", ["english", "same"],
                          format_func=lambda x: "English" if x == "english" else "Same as review (Tamil/Tanglish)")


def llm_or_stop():
    try:
        return get_llm(api_key, model)
    except MissingAPIKeyError as e:
        st.error(str(e))
        st.stop()


# ------------------------------------------------------------------ header
ui.hero(model)
steps_ph = st.empty()


def show_step(active: int) -> None:
    steps_ph.markdown(ui.stepper_html(active), unsafe_allow_html=True)


# ------------------------------------------------------------------ 01 upload + 02 validate
ui.section("01", "Upload this week's reviews", "CSV · up to 20 MB · English, Tamil or Tanglish")
with st.container(key="card_upload"):
    c1, c2 = st.columns([3, 1], vertical_alignment="center")
    with c1:
        up = st.file_uploader("CSV with columns: review_id, date, platform, rating, review_text", type=["csv"])
    with c2:
        use_sample = st.button("✨ Try with sample data", width="stretch", type="primary",
                               disabled=not SAMPLE.exists())
        if SAMPLE.exists():
            st.download_button("⬇️ Download sample CSV", SAMPLE.read_bytes(), "reviews_week40.csv", "text/csv",
                               width="stretch")

    with st.expander("📈 Optional: compare with last week (upload last week's ReviewLens export)"):
        prev_up = st.file_uploader("Last week's enriched CSV", type=["csv"], key="prev")
        if prev_up is not None:
            try:
                ss.prev_df = load_enriched(prev_up)
                ss.prev_stats = compute_stats(ss.prev_df)
                st.success(f"Loaded {len(ss.prev_df)} reviews from last week. Trend arrows enabled.")
            except Exception as e:  # noqa: BLE001
                ss.prev_df = ss.prev_stats = None
                st.error(f"Could not load last week's file: {e}")
        else:
            ss.prev_df = ss.prev_stats = None

source, sig = None, None
if up is not None:
    data = up.getvalue()
    source, sig = data, hashlib.sha1(data).hexdigest()
elif use_sample or ss.src_sig == "sample":
    source, sig = SAMPLE.read_bytes(), "sample"

if source is not None and sig != ss.src_sig:
    reset_results()
    try:
        ss.raw, ss.vreport = validate_reviews(source, max_rows=settings.max_rows)
        ss.src_sig = sig
    except CSVValidationError as e:
        ss.raw = ss.vreport = ss.src_sig = None
        st.error(f"❌ {e}")

if ss.raw is None:
    show_step(1)
    ui.section("✦", "What ReviewLens does for you")
    ui.landing_features()
    ui.footer(__version__)
    st.stop()

show_step(3 if ss.enriched is None else 7)

vr = ss.vreport
msg = f"✅ {vr.rows_kept} reviews ready (read {vr.rows_read})."
if vr.dropped:
    msg += " Dropped: " + ", ".join(f"{n} × {r}" for r, n in vr.dropped.items()) + "."
st.success(msg)
for w in vr.warnings:
    st.warning(w)
with st.expander("Preview input", expanded=ss.enriched is None):
    st.dataframe(ss.raw, width="stretch", hide_index=True, height=260)

# ------------------------------------------------------------------ 03 classify + 04 aggregate + 05 report
ui.section("02", "Analyse", "classify → aggregate → weekly report")
with st.container(key="card_analyse"):
    a1, a2 = st.columns([1, 3], vertical_alignment="center")
    run = a1.button(f"🚀 Analyse {len(ss.raw)} reviews", type="primary", width="stretch")
    if ss.enriched is not None:
        a2.markdown(f"✅ Analysed in **{ss.run_secs:.0f}s** with `{model}`. Click again to re-run.")
    else:
        a2.markdown(f"Runs **{len(ss.raw)}** classification calls on `{model}` "
                    f"(concurrency {concurrency}), then writes the weekly report: "
                    f"about {len(ss.raw) + 3} LLM calls in total.")

if run:
    llm = llm_or_stop()
    bar = st.progress(0.0, text="Starting…")
    t0 = time.time()

    def on_progress(done, total, label):
        el = time.time() - t0
        eta = (el / done * (total - done)) if done else 0
        bar.progress(min(done / max(total, 1), 1.0), text=f"{label}: {done}/{total}  ·  ETA {eta:.0f}s")

    try:
        enriched = classify_reviews(ss.raw, llm, reply_mode=reply_mode, max_concurrency=concurrency,
                                    progress=on_progress)
        bar.progress(1.0, text="Writing weekly report…")
        with st.spinner("Grouping themes and writing the weekly report…"):
            enriched, stats, insights, report, _ = build_weekly_report(enriched, llm, ss.prev_df)
    except Exception as e:  # noqa: BLE001
        bar.empty()
        st.error(f"Analysis failed: {type(e).__name__}: {e}")
        st.stop()
    ss.enriched, ss.stats, ss.insights, ss.report = enriched, stats, insights, report
    ss.run_secs = time.time() - t0
    bar.empty()
    st.rerun()

if ss.enriched is None:
    st.stop()

df: pd.DataFrame = ss.enriched
stats = ss.stats
prev = ss.prev_stats
# Re-render report if last-week file was added/removed after the run (numbers only, no LLM call)
report_text = render_report(stats, ss.insights, prev)
tr = trend(stats, prev)
ok = ok_rows(df)

# ------------------------------------------------------------------ 06 show + export
ui.section("03", "Results", f"{stats.date_from} → {stats.date_to}" if stats.date_from else "")
if stats.needs_review:
    st.warning(f"{stats.needs_review} review(s) could not be analysed after retries and are marked "
               f"**needs review** (see the 'Needs review' tab).")

m = st.columns(5)
m[0].metric("Reviews", stats.total, delta=(tr["total"]["total"] if tr else None))
m[1].metric("Positive", f"{stats.sentiment_pct['positive']:g}%",
            delta=(f"{tr['sentiment_pct']['positive']:+g} pts" if tr else None))
m[2].metric("Negative", f"{stats.sentiment_pct['negative']:g}%",
            delta=(f"{tr['sentiment_pct']['negative']:+g} pts" if tr else None), delta_color="inverse")
m[3].metric("🚨 High urgency", len(stats.urgent_ids),
            delta=(tr["urgency"]["high"] if tr else None), delta_color="inverse")
m[4].metric("Avg rating", f"{stats.avg_rating:g}" if stats.avg_rating is not None else "–",
            delta=(tr["avg_rating"]["avg_rating"] if tr and tr["avg_rating"]["avg_rating"] else None))

tabs = st.tabs(["📊 Overview", "📋 Reviews", "🚨 Urgent queue", "📝 Weekly report",
                f"⚠️ Needs review ({stats.needs_review})"])

# --- Overview
with tabs[0]:
    a, b = st.columns(2)
    with a.container(key="card_c1"):
        sc = counts(ok, "sentiment", SENTIMENTS).query("count > 0")
        fig = px.pie(sc, names="sentiment", values="count", hole=0.55, color="sentiment",
                     color_discrete_map=SENT_COLORS, title="Sentiment split")
        fig.update_traces(textinfo="percent+label", sort=False)
        fig.update_layout(showlegend=False)
        st.plotly_chart(ui.style_fig(fig, 340), width="stretch", config=PLOT_CFG)
    with b.container(key="card_c2"):
        cat = (ok.groupby(["category", "sentiment"]).size().reset_index(name="count"))
        fig = px.bar(cat, y="category", x="count", color="sentiment", orientation="h",
                     color_discrete_map=SENT_COLORS, title="Reviews by category",
                     category_orders={"category": list(CATEGORIES), "sentiment": list(SENTIMENTS)})
        fig.update_layout(yaxis_title=None, xaxis_title="reviews")
        st.plotly_chart(ui.style_fig(fig, 340), width="stretch", config=PLOT_CFG)
    a, b = st.columns(2)
    with a.container(key="card_c3"):
        uc = counts(ok, "urgency", URGENCIES)
        fig = px.bar(uc, x="urgency", y="count", color="urgency", color_discrete_map=URG_COLORS,
                     text="count", title="Urgency")
        fig.update_layout(showlegend=False, xaxis_title=None)
        st.plotly_chart(ui.style_fig(fig, 300), width="stretch", config=PLOT_CFG)
    with b.container(key="card_c4"):
        pc = (df.groupby(["platform", "sentiment"]).size().reset_index(name="count")
              .query("sentiment != ''"))
        fig = px.bar(pc, x="platform", y="count", color="sentiment", color_discrete_map=SENT_COLORS,
                     title="Platform × sentiment", category_orders={"sentiment": list(SENTIMENTS)})
        fig.update_layout(xaxis_title=None)
        st.plotly_chart(ui.style_fig(fig, 300), width="stretch", config=PLOT_CFG)
    if tr:
        st.markdown("**Category change vs last week**")
        st.dataframe(pd.DataFrame([{"category": k, "this week": stats.category[k],
                                    "last week": prev.category.get(k, 0),
                                    "change": f"{arrow(d)} {d:+d}"} for k, d in tr["category"].items()]),
                     hide_index=True, width="stretch")

# --- Reviews table with filters
SHOW_COLS = ["review_id", "date", "platform", "rating", "sentiment", "category", "urgency", "language",
             "summary", "suggested_reply", "review_text", "theme", "status"]
with tabs[1]:
    f1, f2, f3, f4 = st.columns([1.2, 2, 2, 2])
    high_only = f1.toggle("🚨 HIGH urgency only", value=False)
    f_sent = f2.multiselect("Sentiment", SENTIMENTS)
    f_cat = f3.multiselect("Category", CATEGORIES)
    f_plat = f4.multiselect("Platform", sorted(df["platform"].unique()))
    g1, g2 = st.columns([2, 4])
    f_lang = g1.multiselect("Language", LANGUAGES)
    q = g2.text_input("Search text", placeholder="biryani, refund, R-1042 …")

    view = df
    if high_only:
        view = view[view["urgency"] == "high"]
    if f_sent:
        view = view[view["sentiment"].isin(f_sent)]
    if f_cat:
        view = view[view["category"].isin(f_cat)]
    if f_plat:
        view = view[view["platform"].isin(f_plat)]
    if f_lang:
        view = view[view["language"].isin(f_lang)]
    if q.strip():
        s = q.strip().lower()
        view = view[view[["review_id", "review_text", "summary"]].astype(str)
                    .apply(lambda col: col.str.lower().str.contains(s, regex=False)).any(axis=1)]

    st.caption(f"Showing {len(view)} of {len(df)} reviews")
    st.dataframe(view[[c for c in SHOW_COLS if c in view]], width="stretch", hide_index=True,
                 height=480, column_config={
                     "summary": st.column_config.TextColumn(width="large"),
                     "suggested_reply": st.column_config.TextColumn(width="large"),
                     "review_text": st.column_config.TextColumn(width="large"),
                     "rating": st.column_config.NumberColumn(format="%d ⭐"),
                 })
    d1, d2 = st.columns(2)
    d1.download_button("⬇️ Download ALL enriched reviews (CSV for Excel)", to_excel_csv(df),
                       f"reviewlens_enriched_{stats.date_to or 'week'}.csv", "text/csv",
                       width="stretch", type="primary")
    d2.download_button(f"⬇️ Download filtered view ({len(view)} rows)", to_excel_csv(view),
                       f"reviewlens_filtered_{stats.date_to or 'week'}.csv", "text/csv",
                       width="stretch")

# --- Urgent queue
with tabs[2]:
    urgent = ok[ok["urgency"] == "high"].sort_values("date")
    if urgent.empty:
        st.success("No high-urgency reviews this week 🎉")
    else:
        st.markdown(f"**{len(urgent)} review(s) need a reply within 24 hours.** "
                    "Copy the suggested reply, adjust if needed, and post it.")
        for _, r in urgent.iterrows():
            stars = "⭐" * int(r["rating"]) if pd.notna(r["rating"]) else "no rating"
            with st.expander(f"🚨 {r['review_id']} · {r['platform']} · {r['date']} · {r['category']} · {stars}"):
                st.markdown(f"**Summary:** {r['summary']}")
                st.markdown(f"**Original ({r['language']}):** {r['review_text']}")
                st.markdown("**Suggested reply:**")
                st.code(r["suggested_reply"], language=None, wrap_lines=True)
        st.download_button("⬇️ Download urgent queue (CSV)", to_excel_csv(urgent),
                           "reviewlens_urgent.csv", "text/csv")

# --- Weekly report
with tabs[3]:
    st.code(report_text, language=None, wrap_lines=True)
    r1, r2 = st.columns(2)
    r1.download_button("⬇️ Download report (.md)", f"```\n{report_text}\n```\n", "weekly_report.md",
                       "text/markdown", width="stretch")
    if r2.button("🔄 Regenerate report text", width="stretch",
                 help="Re-runs only the report chain. Numbers stay the same (computed in pandas)."):
        with st.spinner("Rewriting…"):
            ss.insights = generate_insights(df, stats, llm_or_stop())
        st.rerun()
    with st.expander("How the numbers are calculated"):
        st.markdown(
            "- All counts and percentages are computed with **pandas** from the table, never by the LLM.\n"
            "- Percentages use the analysed reviews (status = ok) as the base.\n"
            "- A *complaint* is a negative review, or a neutral one with medium/high urgency.\n"
            "- Themes: each review gets a short `topic`; the LLM only groups topics into themes, "
            "pandas counts reviews per theme.")

# --- Needs review
with tabs[4]:
    nr = df[df["status"] == STATUS_NEEDS_REVIEW]
    if nr.empty:
        st.success("Every review was analysed successfully, and all values are from the allowed lists.")
    else:
        st.dataframe(nr[["review_id", "platform", "review_text", "attempts", "error"]],
                     hide_index=True, width="stretch")
        if st.button(f"🔁 Retry {len(nr)} review(s)"):
            llm = llm_or_stop()
            with st.spinner("Retrying…"):
                fixed = retry_needs_review(df, llm, reply_mode=reply_mode, max_concurrency=concurrency)
                ss.enriched, ss.stats, ss.insights, ss.report, _ = build_weekly_report(fixed, llm, ss.prev_df)
            st.rerun()

ui.footer(__version__)
