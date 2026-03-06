from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from skill_audit.client import AnthropicClient, GoogleClient, OpenAICompatClient
from skill_audit.providers import build_client, format_runtime_hint, resolve_api_key, resolve_base_url


class ProviderTests(unittest.TestCase):
    def test_resolve_base_url_prefers_override_then_env_then_default(self) -> None:
        self.assertEqual(resolve_base_url("ollama", "http://custom"), "http://custom")
        with patch.dict(os.environ, {"GOOGLE_BASE_URL": "https://override.example"}, clear=False):
            self.assertEqual(resolve_base_url("google", None), "https://override.example")
        self.assertEqual(resolve_base_url("openai", None), "https://api.openai.com/v1")

    def test_resolve_api_key_uses_env_and_raises_when_required(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "token"}, clear=False):
            self.assertEqual(resolve_api_key("openai", None), "token")
        self.assertEqual(resolve_api_key("ollama", None), "")
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "Missing Google API key"):
                resolve_api_key("google", None)

    def test_build_client_returns_provider_specific_clients(self) -> None:
        self.assertIsInstance(build_client("openai", base_url="https://a", api_key="x"), OpenAICompatClient)
        self.assertIsInstance(build_client("anthropic", base_url="https://a", api_key="x"), AnthropicClient)
        self.assertIsInstance(build_client("google", base_url="https://a", api_key="x"), GoogleClient)

    def test_format_runtime_hint_matches_provider(self) -> None:
        self.assertIn("Ollama", format_runtime_hint("ollama", base_url="http://localhost", error=RuntimeError("x")) or "")
        self.assertIn(
            "insufficient balance",
            format_runtime_hint("minimax", base_url="https://api.minimax.io/v1", error=RuntimeError("(1008)")) or "",
        )
        self.assertIn(
            "GOOGLE_API_KEY",
            format_runtime_hint("google", base_url="https://google", error=RuntimeError("x")) or "",
        )


if __name__ == "__main__":
    unittest.main()
