"""Tools given to the agents."""
from __future__ import annotations

import os
import threading
import time
from typing import Type

from crewai.tools import BaseTool
from crewai_tools import FileWriterTool, ScrapeWebsiteTool, SerperDevTool
from pydantic import BaseModel, Field

MAX_SCRAPE_CHARS = 6000
_DDG_LOCK = threading.Lock()


class SearchInput(BaseModel):
    search_query: str = Field(..., description="The web search query to run")


class DuckDuckGoSearchTool(BaseTool):
    """Free fallback search used when no Serper key is configured."""

    name: str = "Search the internet"
    description: str = (
        "Search the web for a query. Returns titles, URLs and snippets of the top results. "
        "Use it to find competitors, prices, menus, reviews and complaints."
    )
    args_schema: Type[BaseModel] = SearchInput

    def _run(self, search_query: str) -> str:
        from ddgs import DDGS

        results, error = [], None
        # Serialise calls (agents may fire several in parallel) and retry, since free
        # DuckDuckGo endpoints rate-limit and time out intermittently.
        with _DDG_LOCK:
            for attempt in range(3):
                try:
                    results = list(DDGS(timeout=15).text(search_query, max_results=8))
                    error = None
                    break
                except Exception as exc:
                    error = exc
                    if "no results" in str(exc).lower():
                        break
                    time.sleep(1.5 * (attempt + 1))
        if error is not None and "no results" not in str(error).lower():
            return f"Search failed: {str(error)[:160]}. Try a different query."
        if not results:
            return "No results found. Try a broader query."
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] {r.get('title', '')}\nURL: {r.get('href', '')}\n{r.get('body', '')}\n")
        return "\n".join(lines)


class LimitedScrapeWebsiteTool(ScrapeWebsiteTool):
    """ScrapeWebsiteTool that trims page text so it fits in the LLM context."""

    def _run(self, **kwargs) -> str:
        try:
            text = super()._run(**kwargs)
        except Exception as exc:
            return f"Could not scrape this page ({exc}). Use search snippets instead."
        text = str(text)
        if len(text) > MAX_SCRAPE_CHARS:
            text = text[:MAX_SCRAPE_CHARS] + "\n...[truncated]"
        return text


def search_tool(serper_api_key: str = "") -> BaseTool:
    if serper_api_key:
        os.environ["SERPER_API_KEY"] = serper_api_key
        return SerperDevTool(n_results=8)
    return DuckDuckGoSearchTool()


def scrape_tool() -> BaseTool:
    return LimitedScrapeWebsiteTool()


def file_writer_tool() -> BaseTool:
    return FileWriterTool()
