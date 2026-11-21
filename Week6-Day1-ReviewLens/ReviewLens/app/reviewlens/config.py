"""Central configuration. Everything is read from the environment (.env) - nothing is hard-coded."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load ONLY this project's .env (ReviewLens/.env or app/.env). A bare load_dotenv() walks up parent
# folders and could silently pick up another project's key. Inside Docker, compose injects env vars.
_HERE = Path(__file__).resolve()
for _candidate in (_HERE.parents[2] / ".env", _HERE.parents[1] / ".env"):
    if _candidate.is_file():
        load_dotenv(_candidate)
        break

SENTIMENTS = ("positive", "neutral", "negative")
CATEGORIES = ("food_quality", "delivery", "price", "staff", "packaging", "app")
URGENCIES = ("low", "medium", "high")
LANGUAGES = ("English", "Tamil", "Tanglish", "Other")

REQUIRED_COLUMNS = ("review_id", "date", "platform", "rating", "review_text")
OUTPUT_FIELDS = ("sentiment", "category", "urgency", "language", "summary", "suggested_reply")

STATUS_OK = "ok"
STATUS_NEEDS_REVIEW = "needs_review"


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "").strip()
    max_concurrency: int = _int("MAX_CONCURRENCY", 8)
    max_retries: int = _int("MAX_RETRIES", 2)          # app-level retries for invalid outputs
    request_timeout: int = _int("REQUEST_TIMEOUT", 60)  # seconds per LLM call
    chunk_size: int = _int("CHUNK_SIZE", 25)            # rows per batch() call (progress granularity)
    max_rows: int = _int("MAX_ROWS", 2000)
    business_name: str = os.getenv("BUSINESS_NAME", "our restaurant").strip()


settings = Settings()

MODEL_CHOICES = ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4o", "gpt-4.1"]
