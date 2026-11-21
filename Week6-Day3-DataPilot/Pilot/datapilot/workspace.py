"""Per-session sandbox folder + dataset profiling."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .config import EXEC_TIMEOUT_SECONDS, WORKSPACE_ROOT


@dataclass
class Workspace:
    """A sandbox directory. AI-written code is executed with this folder as its working directory."""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])

    @property
    def root(self) -> Path:
        p = WORKSPACE_ROOT / self.session_id
        (p / "data").mkdir(parents=True, exist_ok=True)
        return p

    # ---------- data ----------
    def save_dataset(self, name: str, content: bytes) -> Path:
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", Path(name).name) or "data.csv"
        dest = self.root / "data" / safe
        dest.write_bytes(content)
        return dest

    def datasets(self) -> list[Path]:
        return sorted(p for p in (self.root / "data").iterdir() if p.is_file())

    # ---------- artifacts ----------
    def charts(self) -> list[Path]:
        return sorted(self.root.glob("*.png"), key=lambda p: p.stat().st_mtime)

    def clear_charts(self) -> None:
        for p in self.root.glob("*.png"):
            p.unlink(missing_ok=True)

    @property
    def script(self) -> Path:
        return self.root / "analysis.py"

    def rerun_script(self, script: Path | None = None) -> tuple[int, str]:
        """Re-run a saved analysis.py exactly as the Executor does (same cwd, same interpreter)."""
        script = script or self.script
        if not script.exists():
            return 1, "analysis.py has not been generated yet."
        env = {**os.environ, "MPLBACKEND": "Agg"}
        proc = subprocess.run(
            [sys.executable, str(script.resolve())],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=EXEC_TIMEOUT_SECONDS,
            env=env,
        )
        return proc.returncode, (proc.stderr or "") + (proc.stdout or "")

    def reset(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def _read_frames(path: Path) -> dict[str, pd.DataFrame]:
    if path.suffix.lower() in (".xlsx", ".xls", ".xlsm"):
        return pd.read_excel(path, sheet_name=None)
    return {"": pd.read_csv(path)}


def load_preview(path: Path) -> dict[str, pd.DataFrame]:
    return _read_frames(path)


def profile_dataset(path: Path, rel_path: str) -> str:
    """Compact, LLM-friendly profile of a CSV/Excel file. Numbers here are facts the agents can rely on."""
    frames = _read_frames(path)
    out: list[str] = [f"DATASET FILE (relative to the working directory): {rel_path}"]
    if len(frames) > 1 or next(iter(frames)) != "":
        out.append(f"Excel workbook with sheets: {list(frames)} -> use pd.read_excel('{rel_path}', sheet_name=<name>)")
    else:
        out.append(f"Load with: pd.read_csv('{rel_path}')")

    for sheet, df in frames.items():
        title = f"SHEET '{sheet}'" if sheet else "TABLE"
        out.append(f"\n{title}: {len(df):,} rows x {df.shape[1]} columns")
        for col in df.columns:
            s = df[col]
            line = f"- {col} ({s.dtype}), nulls={int(s.isna().sum())}"
            if pd.api.types.is_numeric_dtype(s):
                line += f", min={s.min():.4g}, max={s.max():.4g}, mean={s.mean():.4g}"
            else:
                parsed = pd.to_datetime(s, errors="coerce", format="mixed") if s.dtype == object else None
                if parsed is not None and parsed.notna().mean() > 0.9:
                    line += f", DATE-LIKE string from {parsed.min().date()} to {parsed.max().date()} (parse with pd.to_datetime)"
                else:
                    uniq = s.dropna().unique()
                    if len(uniq) <= 15:
                        line += f", values={list(map(str, uniq))}"
                    else:
                        line += f", {len(uniq)} distinct e.g. {list(map(str, uniq[:5]))}"
            out.append(line)
        out.append("Sample rows:\n" + df.head(3).to_csv(index=False).strip())
    return "\n".join(out)
