"""Pydantic models that force the LLM to return valid, typed JSON."""
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field, field_validator

Sentiment = Literal["positive", "neutral", "negative"]
Category = Literal["food_quality", "delivery", "price", "staff", "packaging", "app"]
Urgency = Literal["low", "medium", "high"]
Language = Literal["English", "Tamil", "Tanglish", "Other"]


class ReviewAnalysis(BaseModel):
    """Structured analysis of a single customer review."""

    sentiment: Sentiment = Field(description="Overall customer mood.")
    category: Category = Field(description="The PRIMARY department the review is about.")
    urgency: Urgency = Field(description="high = reply today; medium = follow up soon; low = no action needed.")
    language: Language = Field(description="Language the review is written in. Tamil words in Latin script mixed with English = Tanglish.")
    summary: str = Field(description="Exactly one short sentence in ENGLISH summarising the review (max 30 words).")
    suggested_reply: str = Field(description="Polite, ready-to-post public reply, 1-3 sentences.")
    topic: str = Field(description="2-4 word lowercase English key phrase for the main point, e.g. 'late delivery', 'biryani taste', 'extra bill charges'.")

    @field_validator("summary", "suggested_reply", "topic")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("must not be empty")
        return v

    @field_validator("summary")
    @classmethod
    def _summary_short(cls, v: str) -> str:
        if len(v.split()) > 45:
            raise ValueError("summary must be one short sentence")
        return v

    @field_validator("topic")
    @classmethod
    def _topic_short(cls, v: str) -> str:
        v = v.lower().strip(" .")
        if len(v.split()) > 6:
            raise ValueError("topic must be 2-4 words")
        return v


# ---------- Reduce step: theme clustering ----------

class Theme(BaseModel):
    name: str = Field(description="Short human-readable theme label in Title case, e.g. 'Late delivery'.")
    topics: List[str] = Field(description="The exact topic strings (copied from the input) that belong to this theme.")


class ThemeClusters(BaseModel):
    themes: List[Theme]


# ---------- Reduce step: weekly report text ----------

class ThemeNote(BaseModel):
    theme: str = Field(description="Theme name exactly as given in the facts.")
    note: str = Field(description="Max 12 words of context, e.g. 'mostly Swiggy dinner orders'. No numbers that are not in the facts.")


class WeeklyInsights(BaseModel):
    headline: str = Field(description="One sentence describing the week overall.")
    complaint_notes: List[ThemeNote] = Field(description="One note per complaint theme provided.")
    praise_notes: List[ThemeNote] = Field(description="One note per praise theme provided.")
    action_items: List[str] = Field(description="Exactly 3 concrete, specific action items for the manager.")

    @field_validator("action_items")
    @classmethod
    def _three(cls, v: List[str]) -> List[str]:
        v = [a.strip() for a in v if a and a.strip()]
        if len(v) < 3:
            raise ValueError("need exactly 3 action items")
        return v[:3]
