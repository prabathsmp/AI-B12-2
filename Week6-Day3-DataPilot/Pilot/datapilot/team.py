"""AutoGen team construction and the agentic run loop.

Planner -> Coder -> Executor -> (error? back to Coder) -> Reviewer -> (feedback? back to Coder) -> APPROVED
Stops on TextMentionTermination("APPROVED", sources=[Reviewer]) | MaxMessageTermination(12).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Sequence

from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent, UserProxyAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import OpenAIChatCompletionClient

from . import prompts
from .config import (
    APPROVAL_TOKEN,
    CODER,
    EXEC_TIMEOUT_SECONDS,
    EXECUTOR,
    PLANNER,
    REVIEWER,
    ROUTING_SELECTOR,
    USER_PROXY,
    RunSettings,
)
from .workspace import Workspace

ERROR_MARKERS = ("exited with an error", "Traceback (most recent call last)", "No code blocks found", "timed out")


def is_execution_error(text: str) -> bool:
    return any(m.lower() in text.lower() for m in ERROR_MARKERS)


def make_model_client(settings: RunSettings) -> OpenAIChatCompletionClient:
    kwargs: dict[str, Any] = {"model": settings.model, "api_key": settings.api_key}
    if settings.base_url:
        kwargs["base_url"] = settings.base_url
        # Unknown models behind compatible endpoints need capability hints.
        kwargs["model_info"] = {
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": "unknown",
            "structured_output": False,
        }
    return OpenAIChatCompletionClient(**kwargs)


def route_next_speaker(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
    """Deterministic routing for SelectorGroupChat. Returning None falls back to LLM-based selection."""
    if not messages:
        return PLANNER
    last = messages[-1]
    src = last.source
    if src in ("user", USER_PROXY):
        return PLANNER
    if src == PLANNER:
        return CODER
    if src == CODER:
        return EXECUTOR
    if src == EXECUTOR:
        return CODER if is_execution_error(last.to_text()) else REVIEWER
    if src == REVIEWER:  # not approved (approval terminates the run) -> back to code
        return CODER
    return None


def build_team(settings: RunSettings, ws: Workspace, model_client: OpenAIChatCompletionClient):
    planner = AssistantAgent(
        PLANNER,
        model_client=model_client,
        system_message=prompts.PLANNER_SYSTEM,
        description="Writes the step-by-step analysis plan.",
    )
    coder = AssistantAgent(
        CODER,
        model_client=model_client,
        system_message=prompts.CODER_SYSTEM + (prompts.CODER_STRESS_TEST_ADDON if settings.stress_test else ""),
        description="Writes and fixes the pandas/matplotlib analysis.py script.",
    )
    executor = CodeExecutorAgent(
        EXECUTOR,
        code_executor=LocalCommandLineCodeExecutor(
            work_dir=ws.root,
            timeout=EXEC_TIMEOUT_SECONDS,
            cleanup_temp_files=False,  # keep analysis.py for download / re-run
        ),
        sources=[CODER],  # only ever execute code written by the Coder
        supported_languages=["python"],
        description="Runs the Coder's Python in the sandbox folder and reports output or errors.",
    )
    reviewer = AssistantAgent(
        REVIEWER,
        model_client=model_client,
        system_message=prompts.REVIEWER_SYSTEM,
        description="Quality gate: approves the result or sends feedback to the Coder.",
    )

    termination = TextMentionTermination(APPROVAL_TOKEN, sources=[REVIEWER]) | MaxMessageTermination(settings.max_messages)
    participants = [planner, coder, executor, reviewer]

    if settings.routing == ROUTING_SELECTOR:
        return SelectorGroupChat(
            participants,
            model_client=model_client,
            termination_condition=termination,
            selector_prompt=prompts.SELECTOR_PROMPT,
            selector_func=route_next_speaker,
            allow_repeated_speaker=False,
        )
    return RoundRobinGroupChat(participants, termination_condition=termination)


@dataclass
class RunOutcome:
    approved: bool
    stop_reason: str
    final_text: str
    state: dict
    messages: list[dict] = field(default_factory=list)


async def stream_analysis(
    settings: RunSettings,
    ws: Workspace,
    task: str,
    prior_state: dict | None = None,
) -> AsyncIterator[BaseChatMessage | RunOutcome]:
    """Run (or continue) the team. Yields every chat message live, then a RunOutcome."""
    model_client = make_model_client(settings)
    try:
        team = build_team(settings, ws, model_client)
        if prior_state:
            await team.load_state(prior_state)

        result: TaskResult | None = None
        async for item in team.run_stream(task=task):
            if isinstance(item, TaskResult):
                result = item
            elif isinstance(item, BaseChatMessage):
                yield item

        state = await team.save_state()
        msgs = list(result.messages) if result else []
        final = next((m.to_text() for m in reversed(msgs) if isinstance(m, BaseChatMessage) and m.source == REVIEWER), "")
        approved = APPROVAL_TOKEN in final
        yield RunOutcome(
            approved=approved,
            stop_reason=(result.stop_reason if result else "unknown") or "",
            final_text=final if approved else "",
            state=state,
        )
    finally:
        await model_client.close()


async def human_turn(text: str) -> str:
    """Human-in-the-loop via AutoGen's UserProxyAgent.

    In a web UI a blocking console prompt is not possible, so the proxy's input_func is wired to what the
    person typed / clicked in the approval panel. The proxy's reply becomes the next task of the team.
    """

    async def from_ui(prompt: str, cancellation_token=None) -> str:  # noqa: ARG001
        return text

    proxy = UserProxyAgent(USER_PROXY, input_func=from_ui)
    result = await proxy.run(task="Review the approved answer. Reply APPROVE or ask a follow-up question.")
    return result.messages[-1].to_text()


SECTION_RE = re.compile(r"^##\s*(ANSWER|WHERE IT CAME FROM|FILES|SUGGESTED NEXT QUESTION)\s*$", re.M | re.I)


def parse_final_answer(text: str) -> dict[str, str]:
    """Split the Reviewer's approved message into its sections."""
    text = text.replace(APPROVAL_TOKEN, "").strip()
    parts = SECTION_RE.split(text)
    sections: dict[str, str] = {}
    for i in range(1, len(parts) - 1, 2):
        sections[parts[i].upper()] = parts[i + 1].strip()
    if not sections:
        sections["ANSWER"] = text
    return sections
