"""Thin LLM wrapper. Works with any OpenAI-compatible provider
(OpenAI, Groq, OpenRouter, Together, local Ollama...).
Falls back to a deterministic stub when no key is set, so the whole
backend still runs offline during development."""
from __future__ import annotations

from loguru import logger

from app.core.config import settings

SYSTEM_PROMPT = (
    "You are an expert enterprise data analyst. You explain datasets, model results "
    "and business implications precisely. Always ground your answer in the provided "
    "CONTEXT. If the context is insufficient, say so explicitly. Never invent numbers."
)

# Providers that don't need a real key (e.g. a local Ollama server)
_PLACEHOLDER_KEYS = {"", "sk-xxxx", "changeme"}


def _is_configured() -> bool:
    if settings.LLM_BASE_URL and "localhost" in settings.LLM_BASE_URL:
        return True  # local server, no key required
    key = (settings.OPENAI_API_KEY or "").strip()
    return key not in _PLACEHOLDER_KEYS and not key.startswith("sk-xxxx")


def chat(prompt: str, system: str | None = None, temperature: float = 0.2,
         max_tokens: int = 900) -> str:
    if not _is_configured():
        logger.warning("No LLM key configured - returning stub answer")
        return ("[LLM disabled - stub response]\n\n"
                "Configure OPENAI_API_KEY in .env to enable generated narratives.\n\n"
                f"Prompt received ({len(prompt)} chars):\n{prompt[:600]}")
    try:
        from openai import OpenAI

        client_kwargs = {"api_key": settings.OPENAI_API_KEY or "not-needed"}
        if settings.LLM_BASE_URL:
            client_kwargs["base_url"] = settings.LLM_BASE_URL
        client = OpenAI(**client_kwargs)

        resp = client.chat.completions.create(
            model=settings.LLM_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": system or SYSTEM_PROMPT},
                      {"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:
        logger.error(f"LLM call failed: {exc}")
        return f"[LLM error] {exc}"