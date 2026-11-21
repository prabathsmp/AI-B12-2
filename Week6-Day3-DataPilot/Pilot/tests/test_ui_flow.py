"""Headless UI test: full ask -> self-fix -> approve -> follow-up flow through the real Streamlit app (fake LLM)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from autogen_ext.models.replay import ReplayChatCompletionClient  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

import datapilot.team as team_mod  # noqa: E402
from tests.test_agent_loop import APPROVE, BAD, GOOD  # noqa: E402


def test_ui_flow() -> None:
    client = ReplayChatCompletionClient(["plan", BAD, GOOD, APPROVE, "plan 2", GOOD, APPROVE])
    client.close = lambda: asyncio.sleep(0)
    team_mod.make_model_client = lambda s: client

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120).run()
    assert not at.exception, at.exception
    at.text_input(key="api_key").set_value("sk-test").run()
    next(b for b in at.button if "Use sample" in b.label).click().run()
    assert not at.exception, at.exception

    at.chat_input[0].set_value("Which category had the biggest revenue drop?").run()
    assert not at.exception, at.exception
    runs = at.session_state["runs"]
    assert len(runs) == 1 and runs[0]["approved"] and runs[0]["charts"] and runs[0]["script"]
    sources = [m["source"] for m in at.session_state["transcript"]]
    assert sources.count("Executor") == 2, sources

    next(b for b in at.button if "Approve final answer" in b.label).click().run()
    assert at.session_state["runs"][0]["human"] == "approved"

    next(b for b in at.button if "Re-run" in b.label).click().run()
    assert any("Reproducible" in s.value for s in at.success), [s.value for s in at.success]

    at.chat_input[0].set_value("Did discounts change?").run()
    assert not at.exception, at.exception
    assert len(at.session_state["runs"]) == 2 and at.session_state["runs"][1]["approved"]
    at.session_state["ws"].reset()
    print("UI flow OK")


if __name__ == "__main__":
    test_ui_flow()
