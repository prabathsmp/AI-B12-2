"""LLM factory. The only place that knows about the provider, so the chains stay model-agnostic."""
from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from .config import settings


class MissingAPIKeyError(RuntimeError):
    pass


def get_llm(api_key: str | None = None, model: str | None = None, temperature: float = 0.0) -> BaseChatModel:
    """Build a chat model. `api_key` comes from the UI at runtime; falls back to OPENAI_API_KEY from .env."""
    key = (api_key or settings.openai_api_key or "").strip()
    if not key:
        raise MissingAPIKeyError("No OpenAI API key. Add OPENAI_API_KEY to .env or paste it in the sidebar.")

    from langchain_openai import ChatOpenAI  # imported lazily so the app starts even without the key

    kwargs = dict(
        model=model or settings.openai_model,
        api_key=key,
        temperature=temperature,
        timeout=settings.request_timeout,
        max_retries=3,  # SDK-level retries with backoff for 429 / 5xx / network errors
    )
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return ChatOpenAI(**kwargs)


def check_key(api_key: str | None, model: str | None = None) -> tuple[bool, str]:
    """Cheap round-trip to verify the key + model work."""
    try:
        llm = get_llm(api_key, model)
        llm.invoke("Reply with the single word: ok", max_tokens=5)
        return True, "API key works."
    except MissingAPIKeyError as e:
        return False, str(e)
    except Exception as e:  # noqa: BLE001 - surface any provider error to the UI
        return False, f"{type(e).__name__}: {str(e)[:300]}"
