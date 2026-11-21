"""Step 04 - Aggregate in pandas. Every number shown in the dashboard or report comes from here, not the LLM."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from .config import CATEGORIES, SENTIMENTS, STATUS_OK, URGENCIES


def ok_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["status"] == STATUS_OK]


def complaint_mask(df: pd.DataFrame) -> pd.Series:
    """A review counts as a complaint if negative, or neutral with medium/high urgency."""
    return (df["sentiment"] == "negative") | ((df["sentiment"] == "neutral") & df["urgency"].isin(["medium", "high"]))


def praise_mask(df: pd.DataFrame) -> pd.Series:
    return df["sentiment"] == "positive"


def pct(part: int, whole: int) -> float:
    return round(100.0 * part / whole, 1) if whole else 0.0


def counts(df: pd.DataFrame, col: str, order: Optional[tuple] = None) -> pd.DataFrame:
    """Count + percentage table for a column, in a fixed order when given (zeros included)."""
    vc = df[col].value_counts()
    if order is not None:
        vc = vc.reindex(list(order), fill_value=0)
    total = int(vc.sum())
    return pd.DataFrame({col: vc.index, "count": vc.values.astype(int),
                         "percent": [pct(int(v), total) for v in vc.values]})


@dataclass
class ThemeStat:
    theme: str
    count: int
    top_platform: str
    top_platform_share: float
    top_category: str
    review_ids: List[str] = field(default_factory=list)


@dataclass
class WeekStats:
    total: int
    analysed: int
    needs_review: int
    date_from: str
    date_to: str
    sentiment: Dict[str, int]
    sentiment_pct: Dict[str, float]
    category: Dict[str, int]
    urgency: Dict[str, int]
    platform: Dict[str, int]
    urgent_ids: List[str]
    avg_rating: Optional[float]
    complaint_themes: List[ThemeStat] = field(default_factory=list)
    praise_themes: List[ThemeStat] = field(default_factory=list)


def _date_range(df: pd.DataFrame) -> tuple[str, str]:
    d = pd.to_datetime(df["date"], errors="coerce").dropna()
    if d.empty:
        return "", ""
    return d.min().strftime("%Y-%m-%d"), d.max().strftime("%Y-%m-%d")


def theme_stats(df: pd.DataFrame, mask: pd.Series, top_n: int = 3) -> List[ThemeStat]:
    if "theme" not in df:
        return []
    sub = df[mask & (df["theme"].fillna("") != "")]
    if sub.empty:
        return []
    out = []
    for theme, g in sub.groupby("theme"):
        plat = g["platform"].value_counts()
        out.append(ThemeStat(
            theme=str(theme),
            count=int(len(g)),
            top_platform=str(plat.index[0]),
            top_platform_share=pct(int(plat.iloc[0]), len(g)),
            top_category=str(g["category"].value_counts().index[0]),
            review_ids=g["review_id"].astype(str).tolist(),
        ))
    out.sort(key=lambda t: (-t.count, t.theme))
    return out[:top_n]


def compute_stats(df: pd.DataFrame, top_n: int = 3) -> WeekStats:
    ok = ok_rows(df)
    total_ok = len(ok)
    sent = ok["sentiment"].value_counts().reindex(list(SENTIMENTS), fill_value=0).astype(int).to_dict()
    date_from, date_to = _date_range(df)
    rating = pd.to_numeric(df["rating"], errors="coerce").dropna()
    return WeekStats(
        total=len(df),
        analysed=total_ok,
        needs_review=int(len(df) - total_ok),
        date_from=date_from,
        date_to=date_to,
        sentiment=sent,
        sentiment_pct={k: pct(v, total_ok) for k, v in sent.items()},
        category=ok["category"].value_counts().reindex(list(CATEGORIES), fill_value=0).astype(int).to_dict(),
        urgency=ok["urgency"].value_counts().reindex(list(URGENCIES), fill_value=0).astype(int).to_dict(),
        platform=df["platform"].value_counts().astype(int).to_dict(),
        urgent_ids=ok.loc[ok["urgency"] == "high", "review_id"].astype(str).tolist(),
        avg_rating=round(float(rating.mean()), 2) if not rating.empty else None,
        complaint_themes=theme_stats(ok, complaint_mask(ok), top_n),
        praise_themes=theme_stats(ok, praise_mask(ok), top_n),
    )


def trend(current: WeekStats, previous: Optional[WeekStats]) -> Dict[str, Dict[str, float]]:
    """Deltas vs last week: percentage-point change for sentiment, absolute change for counts."""
    if previous is None:
        return {}
    return {
        "sentiment_pct": {k: round(current.sentiment_pct[k] - previous.sentiment_pct.get(k, 0.0), 1)
                          for k in SENTIMENTS},
        "category": {k: current.category[k] - previous.category.get(k, 0) for k in CATEGORIES},
        "urgency": {k: current.urgency[k] - previous.urgency.get(k, 0) for k in URGENCIES},
        "total": {"total": current.total - previous.total},
        "avg_rating": {"avg_rating": round((current.avg_rating or 0) - (previous.avg_rating or 0), 2)
                       if current.avg_rating is not None and previous.avg_rating is not None else 0.0},
    }


def arrow(delta: float) -> str:
    return "→" if delta == 0 else ("▲" if delta > 0 else "▼")
