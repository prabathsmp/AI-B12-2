"""Step 03 - Classify every review (the MAP step).

prompt | llm.with_structured_output(ReviewAnalysis)  ->  chain.batch(..., max_concurrency=N)
Invalid outputs are retried automatically; rows that still fail are marked 'needs_review'.
"""
from __future__ import annotations

import time
from typing import Callable, List, Optional

import pandas as pd
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from .config import (CATEGORIES, LANGUAGES, SENTIMENTS, STATUS_NEEDS_REVIEW, STATUS_OK,
                     URGENCIES, settings)
from .schemas import ReviewAnalysis

SYSTEM_PROMPT = """You are a customer-feedback analyst for {business_name}, an Indian food business \
that receives reviews on Google, Zomato, Swiggy and Amazon. Reviews may be in English, Tamil \
(Tamil script) or Tanglish (Tamil written in Latin letters, mixed with English).

Analyse ONE review and return the structured fields.

RULES
- sentiment: positive | neutral | negative. Mixed reviews: pick the dominant feeling; a clear complaint \
alongside praise is usually "negative" if the complaint is about money, safety or a wrong order, else "neutral".
- category: the PRIMARY topic, exactly one of: food_quality (taste, freshness, temperature, portion, hygiene \
of food), delivery (late, delivery partner, wrong address, cold on arrival because of delay), price \
(bill, extra charges, value for money, refunds), staff (behaviour, service at outlet, phone support), \
packaging (spills, leaks, containers, neatness), app (ordering app/website, payment flow, coupons, tracking).
- urgency:
  high   = must reply TODAY: food poisoning / illness, foreign object (hair, insect, plastic), stale or \
spoiled food, wrong or missing order/items, refund or payment dispute, rude/abusive staff, threats \
(legal, police, consumer court), or a severe delivery failure (very late AND food cold/inedible).
  medium = a clear complaint that needs follow-up (late, cold, overcharged, small portion, app glitch).
  low    = positive or neutral feedback, or a minor suggestion.
- language: English | Tamil | Tanglish | Other.
- summary: ONE sentence in ENGLISH (max 30 words), factual, third person. Translate Tamil/Tanglish faithfully; \
keep specific details (times, items, amounts).
- suggested_reply: {reply_language_rule} Polite, warm, 1-3 sentences, ready to post publicly. \
Apologise for complaints, thank for praise. For complaints ask them to DM/share their order ID. \
Never promise specific refunds, amounts or discounts, never admit legal liability, never invent facts.
- topic: 2-4 lowercase English words naming the main point (e.g. "late delivery", "biryani taste", \
"extra bill charges", "rude delivery partner", "neat packaging").

EXAMPLES
Review (Google, 2*): "Saapadu nalla irundhuchu but bill la extra charge pottanga"
-> sentiment=negative, category=price, urgency=medium, language=Tanglish,
   summary="The food was good but the customer was charged extra on the bill.", topic="extra bill charges"
Review (Swiggy, 1*): "Ordered at 8pm, came at 9:10. Food fully cold. Very bad."
-> sentiment=negative, category=delivery, urgency=high, language=English,
   summary="Order arrived 70 minutes late and the food was cold.", topic="late delivery"
Review (Zomato, 5*): "பிரியாணி மிகவும் சுவையாக இருந்தது"
-> sentiment=positive, category=food_quality, urgency=low, language=Tamil,
   summary="The customer found the biryani very tasty.", topic="biryani taste"
"""

HUMAN_PROMPT = """review_id: {review_id}
platform: {platform}
rating: {rating}
review_text: \"\"\"{review_text}\"\"\""""

REPLY_RULES = {
    "english": "Write the reply in English.",
    "same": "Write the reply in the SAME language and script as the review (English -> English, Tamil "
            "script -> Tamil script, Tanglish -> Tanglish).",
}


def build_classify_chain(llm: BaseChatModel) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", HUMAN_PROMPT)])
    structured = llm.with_structured_output(ReviewAnalysis, method="json_schema", strict=True)
    return prompt | structured


def _to_input(row: pd.Series, reply_mode: str) -> dict:
    rating = row.get("rating")
    return {
        "business_name": settings.business_name,
        "reply_language_rule": REPLY_RULES.get(reply_mode, REPLY_RULES["english"]),
        "review_id": row["review_id"],
        "platform": row["platform"],
        "rating": "not given" if pd.isna(rating) else f"{int(rating)}/5",
        "review_text": str(row["review_text"])[:4000],
    }


def _is_valid(result) -> bool:
    """Belt-and-braces check on top of Pydantic: every enum must be in the allowed list."""
    return (
        isinstance(result, ReviewAnalysis)
        and result.sentiment in SENTIMENTS
        and result.category in CATEGORIES
        and result.urgency in URGENCIES
        and result.language in LANGUAGES
    )


def classify_reviews(
    df: pd.DataFrame,
    llm: BaseChatModel,
    *,
    reply_mode: str = "english",
    max_concurrency: int | None = None,
    max_retries: int | None = None,
    chunk_size: int | None = None,
    progress: Optional[Callable[[int, int, str], None]] = None,
    chain: Runnable | None = None,
) -> pd.DataFrame:
    """Return df enriched with the analysis columns + status/error. Never raises for a single bad row."""
    chain = chain or build_classify_chain(llm)
    max_concurrency = max_concurrency or settings.max_concurrency
    max_retries = settings.max_retries if max_retries is None else max_retries
    chunk_size = chunk_size or settings.chunk_size

    inputs = [_to_input(r, reply_mode) for _, r in df.iterrows()]
    n = len(inputs)
    results: List[Optional[ReviewAnalysis]] = [None] * n
    errors: List[str] = [""] * n
    attempts: List[int] = [0] * n

    def run(indices: List[int], label: str, done_offset: int, total: int) -> None:
        for start in range(0, len(indices), chunk_size):
            idx = indices[start:start + chunk_size]
            outs = chain.batch([inputs[i] for i in idx], config={"max_concurrency": max_concurrency},
                               return_exceptions=True)
            for i, out in zip(idx, outs):
                attempts[i] += 1
                if _is_valid(out):
                    results[i], errors[i] = out, ""
                else:
                    errors[i] = (f"{type(out).__name__}: {str(out)[:200]}" if isinstance(out, Exception)
                                 else f"invalid output: {out!r}"[:200])
            if progress:
                progress(done_offset + min(start + chunk_size, len(indices)), total, label)

    # First pass over everything
    run(list(range(n)), "Classifying", 0, n)

    # Automatic retries for rows that failed or returned invalid values
    for attempt in range(1, max_retries + 1):
        failed = [i for i in range(n) if results[i] is None]
        if not failed:
            break
        time.sleep(min(2 * attempt, 5))  # small pause helps with transient rate limits
        run(failed, f"Retrying {len(failed)} review(s), attempt {attempt}/{max_retries}", 0, len(failed))

    return _merge(df, results, errors, attempts)


def _merge(df: pd.DataFrame, results, errors, attempts) -> pd.DataFrame:
    out = df.copy()
    rows = []
    for res, err in zip(results, errors):
        if res is not None:
            d = res.model_dump()
            d.update(status=STATUS_OK, error="")
        else:
            d = dict(sentiment="", category="", urgency="", language="", summary="",
                     suggested_reply="", topic="", status=STATUS_NEEDS_REVIEW, error=err)
        rows.append(d)
    enriched = pd.DataFrame(rows, index=out.index)
    for col in enriched.columns:
        out[col] = enriched[col]
    out["attempts"] = attempts
    return out


ANALYSIS_COLS = ["sentiment", "category", "urgency", "language", "summary", "suggested_reply",
                 "topic", "status", "error", "attempts"]


def retry_needs_review(df: pd.DataFrame, llm: BaseChatModel, **kwargs) -> pd.DataFrame:
    """Re-run only the rows marked needs_review and merge them back."""
    mask = df["status"] == STATUS_NEEDS_REVIEW
    if not mask.any():
        return df
    base_cols = [c for c in df.columns if c not in ANALYSIS_COLS + ["theme"]]
    redo = classify_reviews(df.loc[mask, base_cols], llm, **kwargs)
    redo["attempts"] = redo["attempts"] + df.loc[mask, "attempts"].to_numpy()
    out = df.copy()
    for c in ANALYSIS_COLS:
        out.loc[mask, c] = redo[c].to_numpy()
    return out
