import unittest
from unittest.mock import MagicMock, patch

from skill_audit.client import (
    AnthropicClient,
    GoogleClient,
    HttpTargetClient,
    OpenAIChatClient,
    _http_post_json,
    chat_json,
    extract_message_content,
    parse_json_from_text,
)


class ClientTests(unittest.TestCase):
    def test_extract_message_content_handles_various_formats(self) -> None:
        self.assertEqual(extract_message_content({"choices": [{"message": {"content": "hi"}}]}), "hi")
        self.assertEqual(extract_message_content({"choices": [{"text": "hello"}]}), "hello")

    @patch("skill_audit.client._http_post_json")
    def test_openai_chat_client_calls_correct_url(self, mock_post) -> None:
        client = OpenAIChatClient("http://api.test", "key")
        mock_post.return_value = {"choices": []}
        client.chat_completions_create(model="m", messages=[], temperature=0.1, max_tokens=123)
        # Check first argument (url)
        self.assertEqual(mock_post.call_args[0][0], "http://api.test/chat/completions")
        self.assertEqual(mock_post.call_args[0][2]["temperature"], 0.1)
        self.assertEqual(mock_post.call_args[0][2]["max_tokens"], 123)

    @patch("skill_audit.client._http_post_json")
    def test_http_target_client_accepts_model_argument(self, mock_post) -> None:
        client = HttpTargetClient("http://api.test/run")
        mock_post.return_value = {"content": "ok"}

        response = client.chat_completions_create(model="ignored-model", messages=[{"role": "user", "content": "hi"}])

        self.assertEqual(mock_post.call_args[0][0], "http://api.test/run")
        self.assertEqual(
            mock_post.call_args[0][2],
            {"model": "ignored-model", "messages": [{"role": "user", "content": "hi"}]},
        )
        self.assertEqual(response["choices"][0]["message"]["content"], "ok")

    @patch("skill_audit.client._http_post_json")
    def test_anthropic_client_uses_system_prompt_and_kwargs(self, mock_post) -> None:
        client = AnthropicClient("https://api.test", "key")
        mock_post.return_value = {"content": [{"type": "text", "text": "ok"}]}
        client.chat_completions_create(
            model="m",
            messages=[
                {"role": "system", "content": "rules"},
                {"role": "user", "content": "hello"},
            ],
            temperature=0.0,
            max_tokens=321,
        )
        payload = mock_post.call_args[0][2]
        self.assertEqual(payload["system"], "rules")
        self.assertEqual(payload["temperature"], 0.0)
        self.assertEqual(payload["max_tokens"], 321)

    @patch("skill_audit.client._http_post_json")
    def test_google_client_requests_json_mode_when_needed(self, mock_post) -> None:
        client = GoogleClient("https://api.test", "key")
        mock_post.return_value = {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}
        client.chat_completions_create(
            model="gemini-test",
            messages=[{"role": "system", "content": "rules"}, {"role": "user", "content": "hello"}],
            temperature=0.0,
            max_tokens=222,
            response_format={"type": "json_object"},
        )
        payload = mock_post.call_args[0][2]
        self.assertEqual(payload["generationConfig"]["temperature"], 0.0)
        self.assertEqual(payload["generationConfig"]["maxOutputTokens"], 222)
        self.assertEqual(payload["generationConfig"]["responseMimeType"], "application/json")
        self.assertEqual(payload["systemInstruction"]["parts"][0]["text"], "rules")

    def test_chat_json_raises_on_invalid_response(self) -> None:
        client = MagicMock()
        client.chat_completions_create.return_value = {"choices": [{"message": {"content": "not json"}}]}
        with self.assertRaises(RuntimeError):
            chat_json(client, model="m", messages=[])

    def test_parse_json_from_text_supports_generic_code_fences(self) -> None:
        data = parse_json_from_text("before\n```text\n{\"ok\": true}\n```\nafter")
        self.assertEqual(data, {"ok": True})

    def test_parse_json_from_text_supports_embedded_arrays(self) -> None:
        data = parse_json_from_text("prefix [1, 2, 3] suffix")
        self.assertEqual(data, [1, 2, 3])

    def test_http_post_json_rejects_insecure_http_with_credentials(self) -> None:
        with self.assertRaises(ValueError):
            _http_post_json(
                "http://example.com/v1/chat/completions",
                {"Content-Type": "application/json", "Authorization": "Bearer sk-test"},
                {"model": "m", "messages": []},
                timeout_s=1,
                max_retries=0,
            )

if __name__ == "__main__":
    unittest.main()
