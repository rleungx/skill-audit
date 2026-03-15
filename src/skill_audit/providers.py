from __future__ import annotations

import os
from dataclasses import dataclass

from .client import AnthropicClient, ChatClient, GoogleClient, HttpTargetClient, OpenAIChatClient


@dataclass(frozen=True)
class ProviderSettings:
    default_base_url: str
    env_api_key: str
    env_base_url: str
    missing_key_message: str


_PROVIDER_SETTINGS = {
    "ollama": ProviderSettings("http://localhost:11434/v1", "", "", ""),
    "openai": ProviderSettings("https://api.openai.com/v1", "OPENAI_API_KEY", "OPENAI_BASE_URL", "Missing OpenAI API key: pass --key or set OPENAI_API_KEY"),
    "minimax": ProviderSettings("https://api.minimax.io/v1", "MINIMAX_API_KEY", "MINIMAX_BASE_URL", "Missing MiniMax API key: pass --key or set MINIMAX_API_KEY"),
    "anthropic": ProviderSettings("https://api.anthropic.com/v1", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "Missing Anthropic API key: pass --key or set ANTHROPIC_API_KEY"),
    "google": ProviderSettings("https://generativelanguage.googleapis.com/v1beta", "GOOGLE_API_KEY", "GOOGLE_BASE_URL", "Missing Google API key: pass --key or set GOOGLE_API_KEY"),
    "xai": ProviderSettings("https://api.x.ai/v1", "XAI_API_KEY", "XAI_BASE_URL", "Missing xAI API key: pass --key or set XAI_API_KEY"),
    "deepseek": ProviderSettings("https://api.deepseek.com", "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "Missing DeepSeek API key: pass --key or set DEEPSEEK_API_KEY"),
    "zhipu": ProviderSettings("https://open.bigmodel.cn/api/paas/v4", "ZHIPU_API_KEY", "ZHIPU_BASE_URL", "Missing Zhipu AI API key: pass --key or set ZHIPU_API_KEY"),
    "groq": ProviderSettings("https://api.groq.com/openai/v1", "GROQ_API_KEY", "GROQ_BASE_URL", "Missing Groq API key: pass --key or set GROQ_API_KEY"),
}

PROVIDER_CHOICES = tuple(_PROVIDER_SETTINGS)


def _get_provider_settings(provider: str) -> ProviderSettings | None:
    return _PROVIDER_SETTINGS.get(provider)


def _api_key_env_var(provider: str) -> str:
    return f"{provider.upper()}_API_KEY"


def resolve_api_key(provider: str, override: str | None) -> str:
    if override:
        return override
    settings = _get_provider_settings(provider)
    if not settings:
        return ""
    if not settings.env_api_key:
        return ""
    key = os.environ.get(settings.env_api_key, "")
    if not key:
        raise ValueError(settings.missing_key_message)
    return key


def resolve_base_url(provider: str, override: str | None) -> str:
    if override:
        return override
    settings = _get_provider_settings(provider)
    if not settings:
        return ""
    if not settings.env_base_url:
        return settings.default_base_url
    return os.environ.get(settings.env_base_url, settings.default_base_url)


def build_client(provider: str, *, base_url: str, api_key: str, timeout_s: int = 60) -> ChatClient:
    if provider == "http":
        return HttpTargetClient(url=base_url, timeout_s=timeout_s)
    if provider == "anthropic":
        return AnthropicClient(base_url=base_url, api_key=api_key, timeout_s=timeout_s)
    if provider == "google":
        return GoogleClient(base_url=base_url, api_key=api_key, timeout_s=timeout_s)
    return OpenAIChatClient(base_url=base_url, api_key=api_key, timeout_s=timeout_s)


def format_runtime_hint(provider: str, base_url: str, error: Exception) -> str:
    error_text = str(error)
    runtime_hint = f"Check your {provider} configuration (Base URL: {base_url})."
    if "403" in error_text:
        runtime_hint += " This might be a regional block or a missing entitlement for the model."
    if "401" in error_text or "403" in error_text:
        runtime_hint += f" Ensure your {_api_key_env_var(provider)} is correct."
    return runtime_hint
