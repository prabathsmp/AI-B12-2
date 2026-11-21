"""Offline end-to-end test of the agentic loop using AutoGen's ReplayChatCompletionClient (no API key needed).

Scenario: Coder's first script raises KeyError -> Executor reports the error -> routing sends it back to the
Coder -> fixed script runs -> Reviewer approves -> run terminates; then a follow-up continues the same session.

Run:  python -m pytest -q tests   (or)   python tests/test_agent_loop.py
"""
from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from autogen_ext.models.replay import ReplayChatCompletionClient  # noqa: E402

import datapilot.team as team_mod  # noqa: E402
from datapilot.config import EXECUTOR, RunSettings  # noqa: E402
from datapilot.team import RunOutcome, human_turn, parse_final_answer, stream_analysis  # noqa: E402
from datapilot.workspace import Workspace, profile_dataset  # noqa: E402

BAD = """```python
# filename: analysis.py
import matplotlib; matplotlib.use("Agg")
import pandas as pd
df = pd.read_csv("data/sales_2026.csv")
print(df["revenue"].sum())
```"""

GOOD = """Fixed: revenue column is now created before it is used.
```python
# filename: analysis.py
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
df = pd.read_csv("data/sales_2026.csv", parse_dates=["order_date"])
df["revenue"] = df["units"] * df["unit_price"] * (1 - df["discount"])
df["month"] = df["order_date"].dt.month
m = df[df.month.isin([8, 9])].pivot_table(index="category", columns="month", values="revenue", aggfunc="sum")
m["drop"] = m[8] - m[9]
top = m["drop"].idxmax()
plt.figure(figsize=(10, 5.5)); (m[[8, 9]] / 1e5).plot(kind="bar", ax=plt.gca())
plt.title("Revenue by category, Aug vs Sep 2026"); plt.xlabel("Category"); plt.ylabel("Revenue (Rs lakh)")
plt.tight_layout(); plt.savefig("category_trend.png", dpi=130); plt.close()
print("CHART | category_trend.png | Revenue by category, Aug vs Sep 2026 | Category | Revenue (Rs lakh)")
print("=== RESULTS ===")
print(f"Biggest drop: {top} Rs {m.loc[top, 'drop'] / 1e5:.2f} L")
```"""

APPROVE = """## ANSWER
Electronics had the biggest drop.

## WHERE IT CAME FROM
South region.

## FILES
category_trend.png, analysis.py

## SUGGESTED NEXT QUESTION
Did discounts change?

APPROVED"""


async def scenario() -> None:
    replies = [
        "1) revenue = units*unit_price*(1-discount) 2) group 3) find drop",  # Planner
        BAD,  # Coder attempt 1
        GOOD,  # Coder attempt 2 (after error)
        APPROVE,  # Reviewer
        # follow-up run
        "1) Compare discount by month for Earbuds X2",  # Planner
        GOOD,  # Coder
        APPROVE,  # Reviewer
    ]
    client = ReplayChatCompletionClient(replies)
    client.close = lambda: asyncio.sleep(0)  # shared across runs in this test
    team_mod.make_model_client = lambda s: client

    ws = Workspace(session_id="pytest_loop")
    shutil.rmtree(ws.root, ignore_errors=True)
    data = ws.save_dataset("sales_2026.csv", (ROOT / "sample_data" / "sales_2026.csv").read_bytes())
    profile = profile_dataset(data, "data/sales_2026.csv")
    settings = RunSettings(api_key="test")

    msgs, outcome = [], None
    async for item in stream_analysis(settings, ws, f"BUSINESS QUESTION: biggest drop?\n{profile}"):
        if isinstance(item, RunOutcome):
            outcome = item
        else:
            msgs.append(item)
    order = [m.source for m in msgs]
    print("Run 1 order:", order)
    assert order == ["user", "Planner", "Coder", "Executor", "Coder", "Executor", "Reviewer"], order
    assert "exited with an error" in msgs[3].to_text() and "KeyError" in msgs[3].to_text()
    assert outcome and outcome.approved, outcome
    assert parse_final_answer(outcome.final_text)["ANSWER"].startswith("Electronics")
    assert (ws.root / "category_trend.png").exists() and ws.script.exists()

    # reproducibility: re-running analysis.py gives the same output as the Executor
    last_exec = [m.to_text() for m in msgs if m.source == EXECUTOR][-1]
    rc, out = ws.rerun_script()
    assert rc == 0 and out.strip().splitlines() == last_exec.strip().splitlines(), (out, last_exec)

    # follow-up continues the same session (state round-trip)
    reply = await human_turn("Did discounts on Earbuds X2 change?")
    msgs2 = []
    async for item in stream_analysis(settings, ws, f"FOLLOW-UP QUESTION: {reply}", outcome.state):
        if isinstance(item, RunOutcome):
            outcome2 = item
        else:
            msgs2.append(item)
    print("Run 2 order:", [m.source for m in msgs2])
    assert outcome2.approved
    shutil.rmtree(ws.root, ignore_errors=True)
    print("OK - self-correction, termination, reproducibility and follow-up verified.")


def test_agent_loop() -> None:
    asyncio.run(scenario())


if __name__ == "__main__":
    test_agent_loop()
