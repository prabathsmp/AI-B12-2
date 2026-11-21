"""Step 02 - Validate the uploaded CSV: check columns, drop empty rows, normalise types."""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd

from .config import REQUIRED_COLUMNS


class CSVValidationError(ValueError):
    """Raised when the CSV cannot be used at all (e.g. missing columns)."""


@dataclass
class ValidationReport:
    rows_read: int = 0
    rows_kept: int = 0
    dropped: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def drop(self, reason: str, n: int) -> None:
        if n:
            self.dropped[reason] = self.dropped.get(reason, 0) + int(n)


def _read_csv(source) -> pd.DataFrame:
    """Read bytes / file-like / path, tolerating UTF-8 (with or without BOM) and Excel's cp1252."""
    if isinstance(source, (bytes, bytearray)):
        raw = bytes(source)
    elif hasattr(source, "getvalue"):
        raw = source.getvalue()
    elif hasattr(source, "read"):
        raw = source.read()
    else:
        with open(source, "rb") as fh:
            raw = fh.read()
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    last_err = None
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(raw), dtype=str, encoding=enc, keep_default_na=False,
                               skipinitialspace=True)
        except UnicodeDecodeError as e:
            last_err = e
        except pd.errors.ParserError as e:
            raise CSVValidationError(f"Could not parse CSV: {e}") from e
        except pd.errors.EmptyDataError as e:
            raise CSVValidationError("The file is empty.") from e
    raise CSVValidationError(f"Unsupported file encoding: {last_err}")


def validate_reviews(source, max_rows: int | None = None) -> tuple[pd.DataFrame, ValidationReport]:
    df = _read_csv(source)
    report = ValidationReport(rows_read=len(df))

    # Normalise column names: trim, lowercase, spaces -> underscores
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise CSVValidationError(
            f"Missing required column(s): {', '.join(missing)}. "
            f"Expected: {', '.join(REQUIRED_COLUMNS)}. Found: {', '.join(df.columns)}"
        )

    extra = [c for c in df.columns if c not in REQUIRED_COLUMNS]
    df = df[list(REQUIRED_COLUMNS) + extra].copy()
    for c in REQUIRED_COLUMNS:
        df[c] = df[c].astype(str).str.strip()

    # Drop fully empty rows, then rows with no review text
    blank_all = (df[list(REQUIRED_COLUMNS)] == "").all(axis=1)
    report.drop("completely empty row", blank_all.sum())
    df = df[~blank_all]

    blank_text = df["review_text"].str.len() == 0
    report.drop("empty review_text", blank_text.sum())
    df = df[~blank_text]

    # review_id: fill blanks, de-duplicate
    df = df.reset_index(drop=True)
    no_id = df["review_id"] == ""
    if no_id.any():
        df.loc[no_id, "review_id"] = [f"AUTO-{i + 1:04d}" for i in df.index[no_id]]
        report.warnings.append(f"{int(no_id.sum())} row(s) had no review_id; generated AUTO-xxxx ids.")
    dup = df["review_id"].duplicated(keep="first")
    report.drop("duplicate review_id", dup.sum())
    df = df[~dup]

    # rating -> Int64 within 1..5 (invalid -> <NA>, row kept)
    rating = pd.to_numeric(df["rating"], errors="coerce")
    bad_rating = rating.notna() & ~rating.between(1, 5)
    rating[bad_rating] = pd.NA
    n_bad = int((rating.isna() & (df["rating"] != "")).sum())
    if n_bad:
        report.warnings.append(f"{n_bad} row(s) had an invalid rating (kept, rating left blank).")
    df["rating"] = rating.round().astype("Int64")

    # date -> ISO string; unparseable kept as-is with a warning
    parsed = pd.to_datetime(df["date"], errors="coerce", format="mixed", dayfirst=False)
    n_bad_date = int((parsed.isna() & (df["date"] != "")).sum())
    if n_bad_date:
        report.warnings.append(f"{n_bad_date} row(s) had an unparseable date (kept as text).")
    df["date"] = parsed.dt.strftime("%Y-%m-%d").where(parsed.notna(), df["date"])

    df["platform"] = df["platform"].replace("", "Unknown")

    if max_rows and len(df) > max_rows:
        report.drop(f"over MAX_ROWS limit ({max_rows})", len(df) - max_rows)
        df = df.head(max_rows)

    df = df.reset_index(drop=True)
    report.rows_kept = len(df)
    if report.rows_kept == 0:
        raise CSVValidationError("No usable reviews after validation (all rows were empty).")
    return df, report
