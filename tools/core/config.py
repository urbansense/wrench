"""LLM configuration resolution from CLI args and environment variables."""

from __future__ import annotations

import os

from wrench.utils.config import LLMConfig

# Env var prefixes checked in order after the CLI arg.
# For each config field, we look up {PREFIX}_{SUFFIX} in this order.
_ENV_PREFIXES = ("LLM", "OLLAMA", "GEMINI")

# Mapping from config field to (env var suffix, default value).
_FIELD_ENV: dict[str, tuple[str, str | None]] = {
    "base_url": ("URL", "http://localhost:11434/v1"),
    "model": ("MODEL", "llama3.3:70b-instruct-q4_K_M"),
    "api_key": ("API_KEY", "ollama"),
    "embedding_model": ("EMBEDDING_MODEL", None),
}


def _resolve_field(
    cli_value: str | None, suffix: str, default: str | None
) -> str | None:
    """Resolve a single config field: CLI arg > env vars > default."""
    if cli_value:
        return cli_value
    for prefix in _ENV_PREFIXES:
        value = os.environ.get(f"{prefix}_{suffix}")
        if value:
            return value
    return default


def resolve_llm_config(
    llm_base_url: str | None = None,
    llm_model: str | None = None,
    llm_api_key: str | None = None,
    embedding_model: str | None = None,
) -> LLMConfig:
    """Resolve LLM configuration from CLI args, then env vars, then defaults.

    Priority order for each field: CLI arg > LLM_* > OLLAMA_* > GEMINI_* > default.

    Args:
        llm_base_url: Explicit base URL (from CLI).
        llm_model: Explicit model name (from CLI).
        llm_api_key: Explicit API key (from CLI).
        embedding_model: Explicit embedding model (from CLI).

    Returns:
        A ready-to-use LLMConfig.
    """
    cli_values = {
        "base_url": llm_base_url,
        "model": llm_model,
        "api_key": llm_api_key,
        "embedding_model": embedding_model,
    }

    resolved = {
        field: _resolve_field(cli_values[field], suffix, default)
        for field, (suffix, default) in _FIELD_ENV.items()
    }

    return LLMConfig(**resolved)
