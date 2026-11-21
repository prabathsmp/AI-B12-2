"""Offline tests - a fake LLM stands in for OpenAI, so no API key or network is needed."""
import sys
from pathlib import Path

import pandas as pd
import pytest
from langchain_core.runnables import RunnableLambda

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from reviewlens.aggregate import compute_stats  # noqa: E402
from reviewlens.classifier import classify_reviews, retry_needs_review  # noqa: E402
from reviewlens.config import CATEGORIES, LANGUAGES, SENTIMENTS, URGENCIES  # noqa: E402
from reviewlens.export import load_enriched, to_excel_csv  # noqa: E402
from reviewlens.report import build_weekly_report  # noqa: E402
from reviewlens.schemas import (ReviewAnalysis, Theme, ThemeClusters, ThemeNote,  # noqa: E402
                                WeeklyInsights)
from reviewlens.validation import CSVValidationError, validate_reviews  # noqa: E402

SAMPLE = Path(__file__).resolve().parents[1] / "app" / "sample_data" / "reviews_week40.csv"


def fake_analysis(text: str) -> ReviewAnalysis:
    t = text.lower()
    if any(w in t for w in ("late", "cold", "delivered", "delivery")):
        return ReviewAnalysis(sentiment="negative", category="delivery", urgency="high" if "cold" in t else "medium",
                              language="English", summary="Delivery was late.", suggested_reply="Sorry!",
                              topic="late delivery")
    if any(w in t for w in ("charge", "bill", "price")):
        return ReviewAnalysis(sentiment="negative", category="price", urgency="medium", language="Tanglish",
                              summary="Extra charges on bill.", suggested_reply="Sorry!", topic="extra charges")
    return ReviewAnalysis(sentiment="positive", category="food_quality", urgency="low", language="English",
                          summary="Customer liked the food.", suggested_reply="Thank you!", topic="biryani taste")


class FakeLLM:
    """Implements just enough of BaseChatModel for our chains."""

    def with_structured_output(self, schema, **_):
        def respond(prompt_value):
            text = prompt_value.to_string()
            if schema is ThemeClusters:
                topics = [ln.strip() for ln in text.splitlines()[1:] if ln.strip() and "topics" not in ln]
                return ThemeClusters(themes=[Theme(name=t.capitalize(), topics=[t]) for t in topics])
            if schema is WeeklyInsights:
                return WeeklyInsights(headline="A busy week.", complaint_notes=[ThemeNote(theme="Late delivery",
                                      note="mostly evenings")], praise_notes=[],
                                      action_items=["Add a rider.", "Show charges.", "Reply to urgent reviews."])
            raise AssertionError(schema)
        return RunnableLambda(respond)


def make_chain(fail_ids=(), always_fail=()):
    seen = {}

    def run(inp):
        rid = inp["review_id"]
        seen[rid] = seen.get(rid, 0) + 1
        if rid in always_fail or (rid in fail_ids and seen[rid] == 1):
            raise ValueError("category 'service' not in allowed list")
        return fake_analysis(inp["review_text"])
    return RunnableLambda(run), seen


@pytest.fixture
def raw():
    df, _ = validate_reviews(SAMPLE)
    return df


# ---------------------------------------------------------------- validation
def test_validation_drops_empty_and_normalises():
    df, rep = validate_reviews(SAMPLE)
    assert rep.rows_read == 40
    assert rep.dropped == {"empty review_text": 1}
    assert len(df) == 39
    assert str(df["rating"].dtype) == "Int64"


def test_validation_missing_column():
    with pytest.raises(CSVValidationError, match="review_text"):
        validate_reviews(b"review_id,date,platform,rating\n1,2026-10-01,Google,5\n")


def test_validation_bom_duplicates_and_header_case():
    csv = "﻿Review_ID, Date ,Platform,Rating,Review Text\nA,2026-10-01,G,5,good\nA,2026-10-01,G,5,dup\n" \
          ",2026-10-02,G,9,ok\n,,,,\n"
    df, rep = validate_reviews(csv.encode("utf-8"))
    assert list(df["review_id"]) == ["A", "AUTO-0003"]
    assert rep.dropped["duplicate review_id"] == 1
    assert rep.dropped["completely empty row"] == 1
    assert pd.isna(df.loc[1, "rating"])


# ---------------------------------------------------------------- classify + retry
def test_classify_all_fields_valid_and_retry(raw):
    chain, seen = make_chain(fail_ids={"R-1042"})
    out = classify_reviews(raw, llm=None, chain=chain, max_retries=2, chunk_size=10)
    assert (out["status"] == "ok").all()
    assert seen["R-1042"] == 2  # failed once, retried automatically
    assert out["sentiment"].isin(SENTIMENTS).all()
    assert out["category"].isin(CATEGORIES).all()
    assert out["urgency"].isin(URGENCIES).all()
    assert out["language"].isin(LANGUAGES).all()
    assert (out["summary"].str.len() > 0).all() and (out["suggested_reply"].str.len() > 0).all()


def test_needs_review_after_retries_then_manual_retry(raw):
    chain, seen = make_chain(always_fail={"R-1043"})
    out = classify_reviews(raw, llm=None, chain=chain, max_retries=2)
    row = out.set_index("review_id").loc["R-1043"]
    assert row["status"] == "needs_review" and row["category"] == "" and "not in allowed list" in row["error"]
    assert seen["R-1043"] == 3

    ok_chain, _ = make_chain()
    import reviewlens.classifier as clf
    orig = clf.build_classify_chain
    clf.build_classify_chain = lambda llm: ok_chain
    try:
        fixed = retry_needs_review(out, llm=None)
    finally:
        clf.build_classify_chain = orig
    assert (fixed["status"] == "ok").all()
    assert fixed.set_index("review_id").loc["R-1043", "attempts"] == 4


# ---------------------------------------------------------------- aggregate + report
def test_report_numbers_match_pandas(raw):
    chain, _ = make_chain()
    enriched = classify_reviews(raw, llm=None, chain=chain)
    themed, stats, insights, text, _ = build_weekly_report(enriched, FakeLLM())

    vc = themed["sentiment"].value_counts()
    assert stats.total == len(themed) == 39
    assert stats.sentiment["negative"] == vc.get("negative", 0)
    assert stats.sentiment_pct["positive"] == round(100 * vc.get("positive", 0) / 39, 1)
    assert len(stats.urgent_ids) == (themed["urgency"] == "high").sum()
    for t in stats.complaint_themes:  # every theme count equals the table
        assert t.count == ((themed["theme"] == t.theme) & (themed["sentiment"] == "negative")).sum()
        assert f"{t.theme} " in text and f"{t.count} reviews" in text
    assert stats.complaint_themes[0].count >= stats.complaint_themes[-1].count
    assert "Total reviews: 39" in text
    assert "29 Sep to 5 Oct 2026" in text
    assert "1. Add a rider." in text


def test_trend_vs_last_week(raw, tmp_path):
    chain, _ = make_chain()
    enriched = classify_reviews(raw, llm=None, chain=chain)
    prev = load_enriched(to_excel_csv(enriched.head(20)))
    _, stats, _, text, prev_stats = build_weekly_report(enriched, FakeLLM(), prev)
    assert prev_stats.total == 20
    assert "CHANGE VS LAST WEEK" in text and "+19" in text


# ---------------------------------------------------------------- export
def test_export_is_excel_safe(raw):
    chain, _ = make_chain()
    enriched = classify_reviews(raw, llm=None, chain=chain)
    enriched.loc[0, "review_text"] = "=HYPERLINK(\"x\")"
    data = to_excel_csv(enriched)
    assert data.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM so Excel reads Tamil correctly
    txt = data.decode("utf-8-sig")
    assert "'=HYPERLINK" in txt
    assert "பிரியாணி" in txt
    header = txt.splitlines()[0].split(",")
    assert header[:11] == ["review_id", "date", "platform", "rating", "review_text", "sentiment", "category",
                           "urgency", "language", "summary", "suggested_reply"]


def test_schema_rejects_invalid_category():
    with pytest.raises(Exception):
        ReviewAnalysis(sentiment="negative", category="service", urgency="high", language="English",
                       summary="x", suggested_reply="y", topic="z")
