from __future__ import annotations

import os
from dataclasses import dataclass

from .client import AnthropicClient, GoogleClient, OpenAICompatClient


@dataclass(frozen=True)
class ProviderSettings:
    default_base_url: str
    env_api_key: str | None = None
    env_base_url: str | None = None
    missing_key_message: str | None = None


_PROVIDER_SETTINGS: dict[str, ProviderSettings] = {
    "ollama": ProviderSettings(default_base_url="http://localhost:11434/v1"),
    "openai": ProviderSettings(
        default_base_url="https://api.openai.com/v1",
        env_api_key="OPENAI_API_KEY",
        missing_key_message="Missing OpenAI API key: pass --key or set OPENAI_API_KEY",
    ),
    "minimax": ProviderSettings(
        default_base_url="https://api.minimax.io/v1",
        env_api_key="MINIMAX_API_KEY",
        env_base_url="MINIMAX_BASE_URL",
        missing_key_message="Missing MiniMax API key: pass --key or set MINIMAX_API_KEY",
    ),
    "anthropic": ProviderSettings(
        default_base_url="https://api.anthropic.com/v1",
        env_api_key="ANTHROPIC_API_KEY",
        env_base_url="ANTHROPIC_BASE_URL",
        missing_key_message="Missing Anthropic API key: pass --key or set ANTHROPIC_API_KEY",
    ),
    "google": ProviderSettings(
        default_base_url="https://generativelanguage.googleapis.com/v1beta",
        env_api_key="GOOGLE_API_KEY",
        env_base_url="GOOGLE_BASE_URL",
        missing_key_message="Missing Google API key: pass --key or set GOOGLE_API_KEY",
    ),
}

PROVIDER_CHOICES: tuple[str, ...] = tuple(_PROVIDER_SETTINGS)
PROVIDER_HELP_TEXT = "ollama (default) / openai / minimax / anthropic / google"


def resolve_base_url(provider: str, override: str | None) -> str:
    if override:
        return override
    settings = _PROVIDER_SETTINGS[provider]
    if settings.env_base_url:
        env_url = os.environ.get(settings.env_base_url)
        if env_url:
            return env_url
    return settings.default_base_url


def resolve_api_key(provider: str, override: str | None) -> str:
    if override:
        return override
    settings = _PROVIDER_SETTINGS[provider]
    if settings.env_api_key:
        env_key = os.environ.get(settings.env_api_key)
        if env_key:
            return env_key
        if settings.missing_key_message:
            raise ValueError(settings.missing_key_message)
    return ""


def build_client(provider: str, *, base_url: str, api_key: str, timeout_s: int = 90):
    if provider == "anthropic":
        return AnthropicClient(base_url=base_url, api_key=api_key, timeout_s=timeout_s)
    if provider == "google":
        return GoogleClient(base_url=base_url, api_key=api_key, timeout_s=timeout_s)
    return OpenAICompatClient(base_url=base_url, api_key=api_key, timeout_s=timeout_s)


def format_runtime_hint(provider: str, *, base_url: str, error: Exception) -> str | None:
    if provider == "ollama":
        return f"(Make sure Ollama is running and reachable at {base_url}.)"

    if provider == "minimax":
        message = str(error).lower()
        if "insufficient balance" in message or "insufficient_balance" in message or "(1008)" in message:
            return (
                "(MiniMax returned insufficient balance: your account quota is insufficient. "
                "Top up or increase quota in the MiniMax console and retry.)"
            )
        if "http 429" in message or "too many requests" in message:
            return "(MiniMax returned 429: rate limited. Retry later or reduce request rate.)"
        return (
            "(Check that your MiniMax API key is correct. If you are in mainland China, try "
            "--url https://api.minimaxi.com/v1; the international default is https://api.minimax.io/v1.)"
        )

    if provider == "anthropic":
        return (
            "(Check that your Anthropic API key is correct (ANTHROPIC_API_KEY / --key) "
            f"and the base_url is reachable: {base_url}.)"
        )
    if provider == "google":
        return (
            "(Check that your Google API key is correct (GOOGLE_API_KEY / --key) "
            f"and the base_url is reachable: {base_url}.)"
        )
    return f"(Check that your API key and base_url are configured correctly: {base_url}.)"
