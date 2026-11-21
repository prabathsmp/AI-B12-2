"""Pluggable LLM / tool settings.

Values come from environment variables (``.env`` via docker-compose) and can be
overridden per session from the UI. Keys are never written to disk or logged.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


@dataclass
class Settings:
    openai_api_key: str = field(default_factory=lambda: _env("OPENAI_API_KEY"))
    model: str = field(default_factory=lambda: _env("OPENAI_MODEL", "gpt-4o-mini"))
    base_url: str = field(default_factory=lambda: _env("OPENAI_BASE_URL"))
    serper_api_key: str = field(default_factory=lambda: _env("SERPER_API_KEY"))
    temperature: float = 0.3
    hierarchical: bool = False
    output_root: str = field(default_factory=lambda: _env("OUTPUT_DIR", "outputs"))

    @property
    def has_llm_key(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def search_provider(self) -> str:
        return "Serper (Google)" if self.serper_api_key else "DuckDuckGo"

    def build_llm(self):
        from crewai import LLM

        model = self.model
        # Plain names like "gpt-4o-mini" go to OpenAI. A custom base URL means an
        # OpenAI-compatible endpoint, which LiteLLM addresses as "openai/<model>".
        if self.base_url and "/" not in model:
            model = f"openai/{model}"
        kwargs = {"model": model, "api_key": self.openai_api_key, "temperature": self.temperature}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return LLM(**kwargs)


def mask(key: str) -> str:
    if not key:
        return "not set"
    return f"{key[:4]}…{key[-4:]}" if len(key) > 10 else "set"
