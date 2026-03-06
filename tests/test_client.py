from __future__ import annotations

import unittest
from unittest.mock import patch

from skill_audit.client import AnthropicClient, GoogleClient, chat_json, parse_json_from_text


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat_completions_create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class ClientTests(unittest.TestCase):
    def test_parse_json_from_text_supports_multiple_formats(self) -> None:
        self.assertEqual(parse_json_from_text('{"ok": true}'), {"ok": True})
        self.assertEqual(parse_json_from_text("```json\n{\"ok\": true}\n```"), {"ok": True})
        self.assertEqual(parse_json_from_text("prefix {\"ok\": true} suffix"), {"ok": True})
        self.assertIsNone(parse_json_from_text("not json"))

    def test_chat_json_falls_back_when_first_response_is_not_json(self) -> None:
        client = FakeClient(
            [
                {"choices": [{"message": {"content": "not valid json"}}]},
                {"choices": [{"message": {"content": '{"ok": true}'}}]},
            ]
        )

        data = chat_json(client, model="demo", messages=[{"role": "user", "content": "hello"}])

        self.assertEqual(data, {"ok": True})
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[0]["response_format"], {"type": "json_object"})
        self.assertIsNone(client.calls[1]["response_format"])

    def test_anthropic_client_transforms_system_prompt_and_extracts_text(self) -> None:
        with patch(
            "skill_audit.client._http_post_json",
            return_value={"content": [{"type": "text", "text": "approved"}]},
        ) as http_post:
            client = AnthropicClient(base_url="https://example.com", api_key="key")
            response = client.chat_completions_create(
                model="claude",
                messages=[
                    {"role": "system", "content": "follow the skill"},
                    {"role": "user", "content": "hello"},
                ],
            )

        payload = http_post.call_args.kwargs["payload"]
        self.assertEqual(payload["system"], "follow the skill")
        self.assertEqual(payload["messages"], [{"role": "user", "content": "hello"}])
        self.assertEqual(response["choices"][0]["message"]["content"], "approved")

    def test_google_client_maps_assistant_role_to_model(self) -> None:
        with patch(
            "skill_audit.client._http_post_json",
            return_value={
                "candidates": [
                    {"content": {"parts": [{"text": "result line 1"}, {"text": "result line 2"}]}}
                ]
            },
        ) as http_post:
            client = GoogleClient(base_url="https://example.com", api_key="key")
            response = client.chat_completions_create(
                model="gemini",
                messages=[
                    {"role": "system", "content": "follow the skill"},
                    {"role": "assistant", "content": "prior"},
                    {"role": "user", "content": "hello"},
                ],
            )

        payload = http_post.call_args.kwargs["payload"]
        self.assertEqual(payload["systemInstruction"], {"parts": [{"text": "follow the skill"}]})
        self.assertEqual(
            payload["contents"],
            [
                {"role": "model", "parts": [{"text": "prior"}]},
                {"role": "user", "parts": [{"text": "hello"}]},
            ],
        )
        self.assertEqual(response["choices"][0]["message"]["content"], "result line 1\nresult line 2")


if __name__ == "__main__":
    unittest.main()
