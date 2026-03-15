import unittest

from skill_audit.providers import format_runtime_hint, resolve_api_key, resolve_base_url


class ProviderTests(unittest.TestCase):
    def test_format_runtime_hint_matches_provider(self) -> None:
        hint = format_runtime_hint("ollama", base_url="http://localhost", error=RuntimeError("x"))
        self.assertIn("ollama", hint)
        self.assertIn("http://localhost", hint)

    def test_format_runtime_hint_suggests_keys_on_403(self) -> None:
        hint = format_runtime_hint("openai", base_url="url", error=RuntimeError("403 Forbidden"))
        self.assertIn("regional block", hint)
        self.assertIn("OPENAI_API_KEY", hint)

    def test_ollama_provider_uses_keyless_defaults(self) -> None:
        self.assertEqual(resolve_api_key("ollama", override=None), "")
        self.assertEqual(resolve_base_url("ollama", override=None), "http://localhost:11434/v1")

if __name__ == "__main__":
    unittest.main()
