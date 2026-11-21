"""Runtime settings for a DataPilot session."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Agent names (also used for routing and UI styling)
PLANNER = "Planner"
CODER = "Coder"
EXECUTOR = "Executor"
REVIEWER = "Reviewer"
USER_PROXY = "User"

APPROVAL_TOKEN = "APPROVED"
DEFAULT_MAX_MESSAGES = 12

MODEL_CHOICES = [
    "gpt-4.1-mini",
    "gpt-4.1",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-5-mini",
    "gpt-5",
]

ROUTING_SELECTOR = "SelectorGroupChat (smart routing)"
ROUTING_ROUND_ROBIN = "RoundRobinGroupChat (fixed turns)"
ROUTING_CHOICES = [ROUTING_SELECTOR, ROUTING_ROUND_ROBIN]

WORKSPACE_ROOT = Path(os.environ.get("DATAPILOT_WORKSPACE", Path(__file__).resolve().parent.parent / "workspaces"))
SAMPLE_DATA = Path(__file__).resolve().parent.parent / "sample_data" / "sales_2026.csv"
EXEC_TIMEOUT_SECONDS = int(os.environ.get("DATAPILOT_EXEC_TIMEOUT", "90"))


@dataclass
class RunSettings:
    api_key: str
    model: str = MODEL_CHOICES[0]
    base_url: str | None = None
    routing: str = ROUTING_SELECTOR
    max_messages: int = DEFAULT_MAX_MESSAGES
    stress_test: bool = False  # ask the Coder to make a deliberate first-draft mistake (demo of self-correction)
