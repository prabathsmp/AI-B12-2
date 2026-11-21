"""Headless UI smoke test: sample data -> analyse -> all tabs render, with a fake LLM."""
import os
import sys
from pathlib import Path

from langchain_core.runnables import RunnableLambda
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import reviewlens.classifier as clf  # noqa: E402
import reviewlens.llm as llm_mod  # noqa: E402
from test_pipeline import FakeLLM, fake_analysis  # noqa: E402


def test_full_flow(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(llm_mod, "get_llm", lambda *a, **k: fake)
    monkeypatch.setattr(clf, "build_classify_chain",
                        lambda llm: RunnableLambda(lambda inp: fake_analysis(inp["review_text"])))
    os.chdir(APP_DIR)
    at = AppTest.from_file(str(APP_DIR / "streamlit_app.py"), default_timeout=60).run()
    assert not at.exception
    next(b for b in at.button if "sample data" in b.label).click().run()
    assert not at.exception
    assert any("39 reviews ready" in s.value for s in at.success)

    next(b for b in at.button if b.label.startswith("🚀 Analyse")).click().run()
    assert not at.exception, at.exception
    assert [m.label for m in at.metric][:4] == ["Reviews", "Positive", "Negative", "🚨 High urgency"]
    codes = "\n".join(c.value for c in at.code)
    assert "WEEKLY FEEDBACK REPORT" in codes and "ACTION ITEMS" in codes

    at.toggle[0].set_value(True).run()  # HIGH urgency only
    assert not at.exception
    assert any("Showing" in c.value for c in at.caption)
