from __future__ import annotations

import json
import os
import random
import socket
import time
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


class ChatClient(Protocol):
    def chat_completions_create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int | None = 800,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


def _split_system_messages(messages: list[dict[str, str]]) -> tuple[str, list[tuple[str, str]]]:
    system_parts: list[str] = []
    non_system_messages: list[tuple[str, str]] = []
    for message in messages:
        role = str(message.get("role", "")).strip().lower()
        content = str(message.get("content", ""))
        if role == "system":
            if content.strip():
                system_parts.append(content.strip())
            continue
        non_system_messages.append((role, content))
    return "\n\n".join(system_parts).strip(), non_system_messages


def _wrap_text_response(content: object, *, raw: object) -> dict[str, Any]:
    return {"choices": [{"message": {"content": str(content or "")}}], "raw": raw}


def _join_text_parts(parts: object) -> str:
    if not isinstance(parts, list):
        return ""
    return "".join(part.get("text", "") for part in parts if isinstance(part, dict))


def _is_localhost(hostname: str | None) -> bool:
    if not hostname:
        return False
    normalized = hostname.strip().lower()
    return normalized in ("localhost", "127.0.0.1", "::1")


def _http_post_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_s: int,
    max_retries: int = 3,
    max_response_bytes: int = 5 * 1024 * 1024,
) -> dict[str, Any]:
    headers = headers.copy()
    headers.setdefault(
        "User-Agent",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    parsed_url = urlparse(url)
    if parsed_url.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed_url.scheme!r}")
    if not parsed_url.netloc:
        raise ValueError(f"Invalid URL: {url!r}")
    allow_insecure_http = os.environ.get("SKILL_AUDIT_ALLOW_INSECURE_HTTP", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    lower_header_keys = {key.lower() for key in headers}
    has_header_credentials = "authorization" in lower_header_keys or "x-api-key" in lower_header_keys
    query_params = parse_qs(parsed_url.query)
    has_query_credentials = any(
        key in query_params and any(len(value) >= 8 for value in query_params.get(key, []))
        for key in ("key", "api_key", "apikey", "token")
    )
    if (
        parsed_url.scheme == "http"
        and (has_header_credentials or has_query_credentials)
        and not allow_insecure_http
        and not _is_localhost(parsed_url.hostname)
    ):
        raise ValueError(
            "Refusing to send credentials over insecure HTTP. Use https or set SKILL_AUDIT_ALLOW_INSECURE_HTTP=1."
        )
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url=url, data=data, headers=headers, method="POST")
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                time.sleep((2**attempt) + random.uniform(0, 1))
            with urlopen(req, timeout=timeout_s) as response:
                body_bytes = response.read(max_response_bytes + 1)
                if len(body_bytes) > max_response_bytes:
                    raise RuntimeError(f"Response too large (>{max_response_bytes} bytes)")
                body = body_bytes.decode("utf-8", errors="replace")
                return json.loads(body)
        except (HTTPError, URLError, socket.timeout, ConnectionError) as e:
            last_err = e
            if isinstance(e, HTTPError) and e.code == 403:
                error_body = e.read(2000).decode("utf-8", "replace")[:200]
                raise RuntimeError(f"HTTP 403 Forbidden: Regional block or WAF. Body: {error_body}") from e
            if attempt >= max_retries:
                raise RuntimeError(f"Request failed: {last_err}")
    raise RuntimeError("Request failed")


class OpenAIChatClient:
    def __init__(self, base_url: str, api_key: str = "", timeout_s: int = 60):
        self._base_url, self._api_key, self._timeout_s = base_url.rstrip("/"), api_key, timeout_s

    def chat_completions_create(self, *, model: str, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        url = f"{self._base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.2),
        }
        if kwargs.get("max_tokens") is not None:
            payload["max_tokens"] = kwargs["max_tokens"]
        if "response_format" in kwargs:
            payload["response_format"] = kwargs["response_format"]
        return _http_post_json(url, headers, payload, self._timeout_s)


class HttpTargetClient:
    def __init__(self, url: str, headers: dict[str, str] | None = None, timeout_s: int = 60):
        self._url, self._headers, self._timeout_s = url, headers or {"Content-Type": "application/json"}, timeout_s

    def chat_completions_create(self, *, model: str, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        payload = {"model": model, "messages": messages}
        raw_response = _http_post_json(self._url, self._headers, payload, self._timeout_s)
        content = _find_text_value(raw_response) or str(raw_response)
        return _wrap_text_response(content, raw=raw_response)


class AnthropicClient:
    def __init__(self, base_url: str, api_key: str, timeout_s: int = 60):
        self._base_url, self._api_key, self._timeout_s = base_url.rstrip("/"), api_key, timeout_s

    def chat_completions_create(self, *, model: str, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        system_prompt, raw_messages = _split_system_messages(messages)
        payload = {
            "model": model,
            "messages": [{"role": role, "content": content} for role, content in raw_messages],
            "max_tokens": kwargs.get("max_tokens", 1024),
            "temperature": kwargs.get("temperature", 0.2),
        }
        if system_prompt:
            payload["system"] = system_prompt
        headers = {"Content-Type": "application/json", "x-api-key": self._api_key, "anthropic-version": "2023-06-01"}
        raw_response = _http_post_json(f"{self._base_url}/messages", headers, payload, self._timeout_s)
        text_blocks = [block for block in raw_response.get("content", []) if block.get("type") == "text"]
        text = _join_text_parts(text_blocks)
        return _wrap_text_response(text, raw=raw_response)


class GoogleClient:
    def __init__(self, base_url: str, api_key: str, timeout_s: int = 60):
        self._base_url, self._api_key, self._timeout_s = base_url.rstrip("/"), api_key, timeout_s

    def chat_completions_create(self, *, model: str, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        system_prompt, raw_messages = _split_system_messages(messages)
        contents = [
            {"role": "model" if role == "assistant" else "user", "parts": [{"text": content}]}
            for role, content in raw_messages
        ]
        generation_config: dict[str, Any] = {"temperature": kwargs.get("temperature", 0.2)}
        if kwargs.get("max_tokens") is not None:
            generation_config["maxOutputTokens"] = kwargs["max_tokens"]
        response_format = kwargs.get("response_format")
        if isinstance(response_format, dict) and response_format.get("type") == "json_object":
            generation_config["responseMimeType"] = "application/json"
        payload = {"contents": contents, "generationConfig": generation_config}
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        raw_response = _http_post_json(
            f"{self._base_url}/models/{model}:generateContent?key={self._api_key}",
            {"Content-Type": "application/json"},
            payload,
            self._timeout_s,
        )
        text = _join_text_parts(raw_response.get("candidates", [{}])[0].get("content", {}).get("parts", []))
        return _wrap_text_response(text, raw=raw_response)


def extract_message_content(response: dict[str, Any]) -> str:
    choices = response.get("choices", [])
    if not choices:
        return ""
    msg = choices[0].get("message", {})
    return msg.get("content", "") or choices[0].get("text", "")


def _find_text_value(payload: object) -> str | None:
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, dict):
        return None
    for key in ("content", "text", "message", "response", "output"):
        if key not in payload:
            continue
        value = payload[key]
        return value.get("content", value) if isinstance(value, dict) else str(value)
    for value in payload.values():
        found = _find_text_value(value)
        if found:
            return found
    return None


def parse_json_from_text(text: str) -> Any | None:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fence_marker = "```"
    if fence_marker in text:
        parts = text.split(fence_marker)
        for block in parts[1::2]:
            candidate = block.split("\n", 1)[1].strip() if "\n" in block else block.strip()
            if not candidate:
                continue
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


def chat_json(client: ChatClient, *, model: str, messages: list[dict[str, str]], temperature: float = 0.2) -> dict[str, Any]:
    response = client.chat_completions_create(
        model=model,
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    content = extract_message_content(response)
    data = parse_json_from_text(content)
    if isinstance(data, dict):
        return data
    raise RuntimeError(f"Failed to parse JSON: {content[:100]}")
