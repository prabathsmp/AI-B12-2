"""The LaunchScout crew: four agents, four tasks, sequential (or hierarchical) process."""
from __future__ import annotations

import os
import threading
import warnings
from datetime import datetime
from pathlib import Path
from typing import Callable

os.environ.setdefault("CREWAI_TELEMETRY_OPT_OUT", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

from crewai import Agent, Crew, Process, Task  # noqa: E402

from .config import Settings  # noqa: E402
from .tools import file_writer_tool, scrape_tool, search_tool  # noqa: E402

EventFn = Callable[[dict], None]
warnings.filterwarnings("ignore", message="A function callback cannot be saved in a checkpoint")

AGENTS = [
    {"key": "researcher", "name": "Market Researcher", "icon": "🔎",
     "blurb": "Finds real competitors, prices, offers and sales channels"},
    {"key": "reviewer", "name": "Review Analyst", "icon": "💬",
     "blurb": "Digs into what customers love and complain about"},
    {"key": "strategist", "name": "Strategy Analyst", "icon": "🧭",
     "blurb": "Builds the matrix, finds the gap, sets price & positioning"},
    {"key": "writer", "name": "Report Writer", "icon": "✍️",
     "blurb": "Writes the founder-friendly report with sources"},
]

SECTIONS = [
    "Key Competitors",
    "What Customers Complain About",
    "Market Gap",
    "Recommended Positioning",
    "30-Day Launch Plan",
    "Sources",
]


def _short(value, limit: int = 220) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _step_callback(agent_key: str, emit: EventFn):
    """Report an agent's final answer for its task (tool calls come from the event bus)."""

    def callback(step) -> None:
        try:
            if hasattr(step, "output") and not getattr(step, "tool", None):
                emit({"type": "step", "agent": agent_key, "kind": "finish",
                      "result": _short(getattr(step, "output", ""), 260)})
        except Exception:  # never let UI plumbing break the crew
            pass

    return callback


# --- live tool activity via the CrewAI event bus ---------------------------------
# Handlers are registered once per process; each run registers its agents' ids so
# events are routed to the right UI session even with concurrent runs.
_ROUTES: dict[str, tuple[str, EventFn]] = {}
_ROUTES_LOCK = threading.Lock()
_HANDLERS_INSTALLED = False


def _route(event) -> tuple[str, EventFn] | None:
    agent_id = getattr(event, "agent_id", None)
    if agent_id is None and getattr(event, "agent", None) is not None:
        agent_id = getattr(event.agent, "id", None)
    with _ROUTES_LOCK:
        return _ROUTES.get(str(agent_id)) if agent_id is not None else None


def _install_handlers() -> None:
    global _HANDLERS_INSTALLED
    if _HANDLERS_INSTALLED:
        return
    from crewai.events import crewai_event_bus
    from crewai.events import ToolUsageErrorEvent, ToolUsageFinishedEvent, ToolUsageStartedEvent

    @crewai_event_bus.on(ToolUsageStartedEvent)
    def _tool_started(source, event):  # noqa: ANN001
        if r := _route(event):
            r[1]({"type": "tool_start", "agent": r[0], "tool": str(event.tool_name),
                  "input": _short(event.tool_args, 180)})

    @crewai_event_bus.on(ToolUsageFinishedEvent)
    def _tool_finished(source, event):  # noqa: ANN001
        if r := _route(event):
            r[1]({"type": "tool_done", "agent": r[0], "tool": str(event.tool_name),
                  "input": _short(event.tool_args, 180), "result": _short(event.output, 260)})

    @crewai_event_bus.on(ToolUsageErrorEvent)
    def _tool_error(source, event):  # noqa: ANN001
        if r := _route(event):
            r[1]({"type": "tool_error", "agent": r[0], "tool": str(event.tool_name),
                  "result": _short(getattr(event, "error", ""), 200)})

    _HANDLERS_INSTALLED = True


def build_crew(settings: Settings, run_dir: Path, emit: EventFn) -> tuple[Crew, list[Task]]:
    llm = settings.build_llm()
    search = search_tool(settings.serper_api_key)
    scrape = scrape_tool()
    writer_tool = file_writer_tool()

    common = dict(llm=llm, verbose=False, allow_delegation=False, max_iter=12)

    researcher = Agent(
        role="Market Researcher",
        goal="Find 3 to 5 real, currently operating competitors for '{idea}' in {city}, "
             "with their prices, offers and sales channels, each backed by a source URL.",
        backstory="You are a sharp local-market researcher who has scouted hundreds of small "
                  "business categories across Indian and global cities. You never invent a "
                  "business: if you cannot find a price on a real page you say 'Not found'. "
                  "You always note the exact URL where each fact came from.",
        tools=[search, scrape],
        step_callback=_step_callback("researcher", emit),
        **common,
    )
    reviewer = Agent(
        role="Review Analyst",
        goal="Discover what customers like and complain about for each competitor of '{idea}' "
             "in {city}, using real reviews, ratings and social posts with source URLs.",
        backstory="You spent years in customer-experience analytics reading Google Maps, "
                  "Zomato, Swiggy, Justdial, Amazon, Reddit and Instagram reviews. You spot "
                  "recurring patterns of pain and delight and quote them faithfully.",
        tools=[search, scrape],
        step_callback=_step_callback("reviewer", emit),
        **common,
    )
    strategist = Agent(
        role="Strategy Analyst",
        goal="Turn the research and reviews into a comparison matrix, the single clearest "
             "market gap, and a priced positioning for a new entrant targeting {customer}.",
        backstory="You are a former management consultant who helps first-time founders find "
                  "a wedge. You reason only from evidence your teammates collected and you "
                  "keep their source URLs attached to every number.",
        tools=[],
        step_callback=_step_callback("strategist", emit),
        **common,
    )
    writer = Agent(
        role="Report Writer",
        goal="Write a clean, founder-friendly competitor report with all 6 required sections "
             "and numbered sources, and save it as report.md.",
        backstory="You are a business writer who turns analyst notes into crisp reports that "
                  "a busy founder can read in five minutes. You keep every citation intact "
                  "and never add facts that are not in your teammates' work.",
        tools=[writer_tool],
        step_callback=_step_callback("writer", emit),
        **common,
    )

    research_task = Task(
        description=(
            "Research the competitive landscape for this business idea.\n"
            "Business idea: {idea}\nCity: {city}\nTarget customer: {customer}\n"
            "Known competitors (may be empty): {known_competitors}\n\n"
            "1. Search the web for businesses already selling something similar in {city} "
            "(also check delivery apps, marketplaces, Instagram and Google Maps listings).\n"
            "2. Pick the 3 to 5 most relevant real competitors (include known competitors if given).\n"
            "3. For each, find price per unit/meal/plan in local currency, offers or subscriptions, "
            "sales channels, one strength and one weakness. Scrape their page when useful, and "
            "try targeted searches like '<name> price', '<name> menu' or their Swiggy/Zomato/"
            "Amazon listing. Prefer competitors whose prices you can verify.\n"
            "4. Record the exact URL for every price and claim. Write 'Not found' rather than guess."
        ),
        expected_output=(
            "A Markdown section titled '## Competitors' with 3 to 5 entries. Each entry is:\n"
            "### <Competitor name>\n- Website: <url>\n- Price: <amount with currency and unit> [source url]\n"
            "- Offers: <offers/subscriptions> [source url]\n- Channels: <e.g. Swiggy, own app, WhatsApp>\n"
            "- Strength: <one line>\n- Weakness: <one line>\n- Sources: <list of URLs>\n"
            "End with '## Search notes' listing queries that worked."
        ),
        agent=researcher,
    )
    review_task = Task(
        description=(
            "For every competitor found by the Market Researcher, search for customer reviews, "
            "ratings and comments (Google Maps, Zomato/Swiggy, Justdial, Reddit, Instagram, "
            "app stores, blogs). Identify what customers like and what they complain about. "
            "Then identify complaints common across competitors. Idea: {idea}, City: {city}."
        ),
        expected_output=(
            "A Markdown section '## Customer Voice'. For each competitor:\n"
            "### <Competitor name>\n- Rating: <x/5 and platform, or 'Not found'> [url]\n"
            "- Likes: 2-4 bullets, each ending with [source url]\n"
            "- Complaints: 2-4 bullets, each ending with [source url]\n"
            "Finish with '## Common complaints' listing 3-5 pain points and which competitors they apply to."
        ),
        agent=reviewer,
        context=[research_task],
    )
    strategy_task = Task(
        description=(
            "Using ONLY the research and review findings, build a strategy for a new entrant "
            "offering '{idea}' in {city} to {customer}.\n"
            "1. Build a comparison matrix of competitors.\n2. Find the single clearest market gap "
            "nobody serves well.\n3. Recommend positioning: a one-line offer with a concrete price "
            "in local currency, and explain the pricing logic against competitor prices."
        ),
        expected_output=(
            "Markdown with:\n## Comparison Matrix\n| Competitor | Price | Channel | Strength | Weakness | Source |\n"
            "(one row per competitor, Source is a URL)\n## Market Gap\nOne short paragraph.\n"
            "## Recommended Positioning\nA quoted one-line offer including a price, then 3 bullets "
            "explaining why it wins and the pricing rationale."
        ),
        agent=strategist,
        context=[research_task, review_task],
    )
    report_path = run_dir / "report.md"
    report_task = Task(
        description=(
            "Write the final competitor report for a founder launching '{idea}' in {city} "
            "for {customer}. Combine the work of the researcher, review analyst and strategist. "
            "Use numbered citations like [1] after every price or claim and list them in Sources. "
            "Add a practical 30-Day Launch Plan (Week 1 to Week 4) tailored to this idea and city.\n"
            f"When the report is complete, save it with the file writer tool using "
            f"filename 'report.md', directory '{run_dir.as_posix()}' and overwrite true. "
            "Then return the full report text as your final answer."
        ),
        expected_output=(
            "A complete Markdown report that starts with '# Competitor Report: {idea}, {city}' "
            "followed by a one-paragraph executive summary, then exactly these sections:\n"
            "## 1. Key Competitors  (table: Competitor | Price | Channel | Strength | Weakness; every Price cell holds the actual amount with currency and unit followed by its [n] citation, or 'Not found')\n"
            "## 2. What Customers Complain About  (bullets, naming competitors, with [n] citations)\n"
            "## 3. Market Gap  (one short paragraph)\n"
            "## 4. Recommended Positioning  (a quoted one-line offer with price, plus rationale)\n"
            "## 5. 30-Day Launch Plan  (Week 1, Week 2, Week 3, Week 4 bullets)\n"
            "## 6. Sources  (numbered list: [n] Title - full URL)\n"
            "No code fences around the report."
        ),
        agent=writer,
        context=[research_task, review_task, strategy_task],
        output_file=str(report_path),
    )

    tasks = [research_task, review_task, strategy_task, report_task]
    agents = [researcher, reviewer, strategist, writer]

    def task_callback(output) -> None:
        role = str(getattr(output, "agent", "")).strip()
        idx = next((i for i, a in enumerate(agents) if a.role == role), -1)
        key = AGENTS[idx]["key"] if idx >= 0 else "unknown"
        emit({"type": "task_done", "agent": key, "output": str(getattr(output, "raw", output))})
        if 0 <= idx < len(AGENTS) - 1 and not settings.hierarchical:
            emit({"type": "agent_start", "agent": AGENTS[idx + 1]["key"]})

    crew_kwargs = dict(agents=agents, tasks=tasks, verbose=False, task_callback=task_callback,
                       max_rpm=30, tracing=False)
    if settings.hierarchical:
        crew_kwargs.update(process=Process.hierarchical, manager_llm=llm)
    else:
        crew_kwargs.update(process=Process.sequential)
    return Crew(**crew_kwargs), tasks


def new_run_dir(root: str) -> Path:
    path = Path(root) / datetime.now().strftime("run_%Y%m%d_%H%M%S")
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def clean_report(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def run_crew(settings: Settings, inputs: dict, emit: EventFn) -> dict:
    """Run the crew end to end. Emits events; returns a result dict."""
    run_dir = new_run_dir(settings.output_root)
    crew, tasks = build_crew(settings, run_dir, emit)
    _install_handlers()
    agent_ids = [str(t.agent.id) for t in tasks]
    with _ROUTES_LOCK:
        for i, agent_id in enumerate(agent_ids):
            _ROUTES[agent_id] = (AGENTS[i]["key"], emit)
    emit({"type": "start", "run_dir": str(run_dir), "search": settings.search_provider})
    if not settings.hierarchical:
        emit({"type": "agent_start", "agent": AGENTS[0]["key"]})
    try:
        result = crew.kickoff(inputs=inputs)
    finally:
        with _ROUTES_LOCK:
            for agent_id in agent_ids:
                _ROUTES.pop(agent_id, None)
    report = clean_report(getattr(result, "raw", str(result)))
    report_path = run_dir / "report.md"
    report_path.write_text(report, encoding="utf-8")
    outputs = {AGENTS[i]["key"]: (t.output.raw if t.output else "") for i, t in enumerate(tasks)}
    usage = getattr(result, "token_usage", None)
    return {
        "report": report,
        "report_path": str(report_path),
        "outputs": outputs,
        "tokens": getattr(usage, "total_tokens", None) if usage else None,
    }
