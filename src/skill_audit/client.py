from __future__ import annotations

import json
import re
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OpenAICompatClient:
    def __init__(self, base_url: str, api_key: str = "", timeout_s: int = 60):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout_s = timeout_s

    def chat_completions_create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int | None = 800,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}/chat/completions"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload: dict[str, Any] = {"model": model, "messages": messages, "temperature": temperature}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format is not None:
            payload["response_format"] = response_format

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = Request(url=url, data=data, headers=headers, method="POST")
        try:
            with urlopen(req, timeout=self._timeout_s) as resp:
                body = resp.read().decode("utf-8", errors="replace")
        except HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            raise RuntimeError(f"HTTP {e.code} {e.reason}: {err_body}".strip()) from e
        except URLError as e:
            raise RuntimeError(f"Request failed: {e}") from e
        except socket.timeout as e:
            raise RuntimeError(f"Request timed out after {self._timeout_s}s") from e

        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Non-JSON response: {body[:500]}") from e


def extract_message_content(resp: dict[str, Any]) -> str:
    choices = resp.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    choice0 = choices[0] if isinstance(choices[0], dict) else {}
    msg = choice0.get("message") if isinstance(choice0, dict) else None
    if isinstance(msg, dict) and isinstance(msg.get("content"), str):
        return msg["content"]
    if isinstance(choice0.get("text"), str):
        return choice0["text"]
    return ""


def parse_json_from_text(text: str) -> Any | None:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    candidate = match.group(0).strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def chat_json(
    client: OpenAICompatClient,
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int | None = 800,
) -> dict[str, Any]:
    last_request_error: Exception | None = None
    last_content: str | None = None
    for response_format in ({"type": "json_object"}, None):
        try:
            resp = client.chat_completions_create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )
        except Exception as e:
            last_request_error = e
            continue

        content = extract_message_content(resp)
        last_content = content
        data = parse_json_from_text(content)
        if isinstance(data, dict):
            return data

    if last_content is not None:
        preview = last_content.strip().replace("\n", " ")[:500]
        raise RuntimeError(f"Model did not return valid JSON. Content preview: {preview}")
    if last_request_error is not None:
        raise last_request_error
    raise RuntimeError("Request failed without a response body.")
