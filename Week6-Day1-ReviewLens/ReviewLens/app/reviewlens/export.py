"""Step 06 - Export. CSV is written as UTF-8 with BOM so Excel shows Tamil text correctly."""
from __future__ import annotations

import pandas as pd

from .config import OUTPUT_FIELDS, REQUIRED_COLUMNS, STATUS_OK
from .validation import _read_csv

EXPORT_COLUMNS = list(REQUIRED_COLUMNS) + list(OUTPUT_FIELDS) + ["topic", "theme", "status", "error"]
_FORMULA_PREFIXES = ("=", "+", "@", "\t", "\r")


def _excel_safe(v):
    """Stop Excel from executing review text as a formula (CSV injection)."""
    if isinstance(v, str) and v.startswith(_FORMULA_PREFIXES):
        return "'" + v
    return v


def to_excel_csv(df: pd.DataFrame) -> bytes:
    cols = [c for c in EXPORT_COLUMNS if c in df.columns] + \
           [c for c in df.columns if c not in EXPORT_COLUMNS and c != "attempts"]
    out = df[cols].copy()
    for c in out.columns:
        if pd.api.types.is_object_dtype(out[c]) or pd.api.types.is_string_dtype(out[c]):
            out[c] = out[c].map(_excel_safe)
    return out.to_csv(index=False, lineterminator="\r\n").encode("utf-8-sig")


def load_enriched(source) -> pd.DataFrame:
    """Load a previously exported enriched CSV (used for last-week comparison)."""
    df = _read_csv(source)
    df.columns = [str(c).strip().lower() for c in df.columns]
    needed = {"review_id", "date", "platform", "rating", "sentiment", "category", "urgency"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"Not a ReviewLens export - missing column(s): {', '.join(sorted(missing))}")
    if "status" not in df:
        df["status"] = STATUS_OK
    for c in ("summary", "topic", "theme"):
        if c not in df:
            df[c] = ""
    return df
