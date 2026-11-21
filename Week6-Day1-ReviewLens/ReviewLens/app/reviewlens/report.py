"""Step 05 - Weekly insights report (the REDUCE step).

1. Theme chain  : clusters the per-review `topic` phrases into a few themes (LLM groups text, never counts).
2. pandas       : counts reviews per theme, sentiment %, urgent count ... (exact numbers).
3. Report chain : given those pre-computed facts, writes short context notes + exactly 3 action items.
4. Renderer     : builds the report; every number is inserted from pandas.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from .aggregate import (WeekStats, arrow, complaint_mask, compute_stats, ok_rows, praise_mask,
                        trend)
from .config import settings
from .schemas import ThemeClusters, WeeklyInsights

# ---------------------------------------------------------------- theme clustering

THEME_SYSTEM = """You group short customer-review topic phrases into themes.
Rules:
- Create between 3 and 10 themes (fewer if there are only a few topics).
- Merge phrases that mean the same thing ("late delivery", "delayed order", "slow delivery" -> "Late delivery").
- Theme names: 2-4 words, Title case first word only, specific (e.g. "Extra charges on bill", "Biryani taste").
- Every input topic must appear in exactly one theme, copied EXACTLY as given.
- Do not count anything."""

THEME_HUMAN = """These are {kind} topics from this week's reviews (one per line):
{topics}"""


def build_theme_chain(llm: BaseChatModel):
    prompt = ChatPromptTemplate.from_messages([("system", THEME_SYSTEM), ("human", THEME_HUMAN)])
    return prompt | llm.with_structured_output(ThemeClusters, method="json_schema", strict=True)


def _cluster(llm: BaseChatModel, topics: List[str], kind: str) -> Dict[str, str]:
    """Return {topic: theme}. Falls back to topic -> Capitalised topic for anything unmapped."""
    uniq = sorted({t for t in topics if t})
    mapping = {t: t.capitalize() for t in uniq}
    if len(uniq) <= 1:
        return mapping
    try:
        res: ThemeClusters = build_theme_chain(llm).with_retry(stop_after_attempt=2).invoke(
            {"kind": kind, "topics": "\n".join(uniq[:600])})
        lower = {t.lower(): t for t in uniq}
        for theme in res.themes:
            for t in theme.topics:
                key = lower.get(t.strip().lower())
                if key:
                    mapping[key] = theme.name.strip()
    except Exception:  # noqa: BLE001 - clustering is best-effort; raw topics are a fine fallback
        pass
    return mapping


def assign_themes(df: pd.DataFrame, llm: BaseChatModel) -> pd.DataFrame:
    """Add a `theme` column (complaint themes for complaints, praise themes for praise)."""
    out = df.copy()
    out["theme"] = ""
    ok = ok_rows(out)
    for kind, mask in (("complaint", complaint_mask(ok)), ("praise", praise_mask(ok))):
        idx = ok.index[mask]
        if len(idx) == 0:
            continue
        mapping = _cluster(llm, out.loc[idx, "topic"].tolist(), kind)
        out.loc[idx, "theme"] = out.loc[idx, "topic"].map(mapping).fillna("")
    return out


# ---------------------------------------------------------------- report text

REPORT_SYSTEM = """You are an operations analyst writing a weekly customer-feedback report for the \
manager of {business_name}. You receive FACTS that were computed exactly with pandas, plus sample \
review summaries. Rules:
- Never invent or change numbers. Only mention a number if it appears in the FACTS.
- complaint_notes / praise_notes: one note per theme listed, max 12 words of useful context \
(when/where/what, e.g. "mostly Swiggy dinner orders", "Tanglish reviews on Google").
- action_items: exactly 3, concrete and doable this week, tied to the biggest complaints and the urgent queue. \
Start each with a verb."""

REPORT_HUMAN = """FACTS (exact):
{facts}

SAMPLE SUMMARIES BY THEME:
{samples}

URGENT REVIEW SUMMARIES:
{urgent}"""


def build_report_chain(llm: BaseChatModel):
    prompt = ChatPromptTemplate.from_messages([("system", REPORT_SYSTEM), ("human", REPORT_HUMAN)])
    return prompt | llm.with_structured_output(WeeklyInsights, method="json_schema", strict=True)


def _facts(stats: WeekStats) -> dict:
    return {
        "date_range": [stats.date_from, stats.date_to],
        "total_reviews": stats.total,
        "analysed": stats.analysed,
        "sentiment_percent": stats.sentiment_pct,
        "category_counts": stats.category,
        "urgency_counts": stats.urgency,
        "platform_counts": stats.platform,
        "urgent_high_count": len(stats.urgent_ids),
        "top_complaint_themes": [
            {"theme": t.theme, "reviews": t.count, "top_platform": t.top_platform,
             "top_platform_share_percent": t.top_platform_share, "category": t.top_category}
            for t in stats.complaint_themes],
        "top_praise_themes": [{"theme": t.theme, "mentions": t.count} for t in stats.praise_themes],
    }


def _samples(df: pd.DataFrame, stats: WeekStats, per_theme: int = 8) -> str:
    lines = []
    by_id = df.set_index(df["review_id"].astype(str))
    for t in stats.complaint_themes + stats.praise_themes:
        lines.append(f"[{t.theme}]")
        for rid in t.review_ids[:per_theme]:
            r = by_id.loc[rid]
            lines.append(f"- ({r['platform']}, {r['date']}) {r['summary']}")
    return "\n".join(lines) or "(none)"


def _fallback_insights(stats: WeekStats) -> WeeklyInsights:
    items = [f"Fix the top complaint: {stats.complaint_themes[0].theme.lower()}."
             if stats.complaint_themes else "Keep monitoring reviews daily.",
             "Review pricing and charge transparency on the menu." if stats.category.get("price") else
             "Share this week's praise with the team.",
             f"Reply to all {len(stats.urgent_ids)} urgent reviews today using the suggested replies."]
    return WeeklyInsights(headline="Weekly feedback summary.", complaint_notes=[], praise_notes=[],
                          action_items=items)


def generate_insights(df: pd.DataFrame, stats: WeekStats, llm: BaseChatModel) -> WeeklyInsights:
    ok = ok_rows(df)
    urgent = ok[ok["urgency"] == "high"]["summary"].head(25).tolist()
    try:
        return build_report_chain(llm).with_retry(stop_after_attempt=2).invoke({
            "business_name": settings.business_name,
            "facts": json.dumps(_facts(stats), indent=2),
            "samples": _samples(ok, stats),
            "urgent": "\n".join(f"- {s}" for s in urgent) or "(none)",
        })
    except Exception:  # noqa: BLE001 - never lose the report because the text step failed
        return _fallback_insights(stats)


# ---------------------------------------------------------------- rendering

def _fmt_range(a: str, b: str) -> str:
    if not a:
        return "date range unknown"
    da, db = datetime.strptime(a, "%Y-%m-%d"), datetime.strptime(b, "%Y-%m-%d")
    if da.year == db.year:
        return f"{da.day} {da:%b} to {db.day} {db:%b %Y}"
    return f"{da.day} {da:%b %Y} to {db.day} {db:%b %Y}"


def _dots(label: str, width: int = 26) -> str:
    return f"{label} " + "." * max(3, width - len(label))


def render_report(stats: WeekStats, insights: WeeklyInsights, prev: Optional[WeekStats] = None) -> str:
    notes_c = {n.theme.lower(): n.note for n in insights.complaint_notes}
    notes_p = {n.theme.lower(): n.note for n in insights.praise_notes}
    tr = trend(stats, prev)
    sp = stats.sentiment_pct

    def s(k: str) -> str:
        base = f"{k.capitalize()} {sp[k]:g}%"
        if tr:
            d = tr["sentiment_pct"][k]
            base += f" ({arrow(d)} {abs(d):g} pts)"
        return base

    L = [f"WEEKLY FEEDBACK REPORT  |  {_fmt_range(stats.date_from, stats.date_to)}", ""]
    L.append(f"Total reviews: {stats.total}   " + "   ".join(s(k) for k in ("positive", "neutral", "negative")))
    if stats.needs_review:
        L.append(f"({stats.analysed} analysed, {stats.needs_review} marked 'needs review' and excluded from %)")
    if stats.avg_rating is not None:
        line = f"Average rating: {stats.avg_rating:g}/5"
        if tr and tr["avg_rating"]["avg_rating"]:
            d = tr["avg_rating"]["avg_rating"]
            line += f" ({arrow(d)} {abs(d):g})"
        L.append(line)
    L.append("")
    L.append(f"{insights.headline}")
    L.append("")
    n_c = len(stats.complaint_themes)
    L.append(f"TOP {n_c} COMPLAINTS" if n_c else "TOP COMPLAINTS")
    if not stats.complaint_themes:
        L.append("No complaints this week.")
    for t in stats.complaint_themes:
        note = notes_c.get(t.theme.lower()) or f"mostly {t.top_platform}"
        L.append(f"{_dots(t.theme)} {t.count} review{'s' if t.count != 1 else ''}  ({note})")
    L.append("")
    if stats.praise_themes:
        praise = ", ".join(
            f"{t.theme.lower() if i else t.theme} ({t.count} mention{'s' if t.count != 1 else ''})"
            for i, t in enumerate(stats.praise_themes))
        L.append(f"TOP PRAISE   {praise}")
    else:
        L.append("TOP PRAISE   none this week")
    L.append("")
    n_urgent = len(stats.urgent_ids)
    L.append(f"URGENT: {n_urgent} review{'s' if n_urgent != 1 else ''} need a reply within 24 hours"
             + (f"  ({', '.join(stats.urgent_ids[:10])}{' ...' if n_urgent > 10 else ''})" if n_urgent else ""))
    L.append("")
    L.append("ACTION ITEMS")
    for i, a in enumerate(insights.action_items, 1):
        L.append(f"  {i}. {a}")
    if tr:
        L.append("")
        L.append("CHANGE VS LAST WEEK")
        L.append(f"  Total reviews: {arrow(tr['total']['total'])} {tr['total']['total']:+d}")
        for k, d in tr["category"].items():
            if d:
                L.append(f"  {k}: {arrow(d)} {d:+d}")
        d = tr["urgency"]["high"]
        L.append(f"  High urgency: {arrow(d)} {d:+d}")
    return "\n".join(L)


def build_weekly_report(df: pd.DataFrame, llm: BaseChatModel, prev_df: Optional[pd.DataFrame] = None):
    """Full reduce pipeline. Returns (df_with_themes, stats, insights, report_text, prev_stats)."""
    themed = assign_themes(df, llm)
    stats = compute_stats(themed)
    insights = generate_insights(themed, stats, llm)
    prev_stats = compute_stats(prev_df) if prev_df is not None else None
    return themed, stats, insights, render_report(stats, insights, prev_stats), prev_stats
