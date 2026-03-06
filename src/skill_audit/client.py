from __future__ import annotations

import json
import socket
from typing import Any, Protocol
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
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


def _http_post_json(*, url: str, headers: dict[str, str], payload: dict[str, Any], timeout_s: int) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url=url, data=data, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout_s) as resp:
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
        raise RuntimeError(f"Request timed out after {timeout_s}s") from e

    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Non-JSON response: {body[:500]}") from e
    if not isinstance(data, dict):
        raise RuntimeError(f"Invalid JSON response (expected object): {body[:500]}")
    return data


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

        payload: dict[str, Any] = {"model": model, "messages": messages}
        if not model.lower().startswith("gpt-5"):
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format is not None:
            payload["response_format"] = response_format

        return _http_post_json(url=url, headers=headers, payload=payload, timeout_s=self._timeout_s)


class AnthropicClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout_s: int = 60,
        anthropic_version: str = "2023-06-01",
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout_s = timeout_s
        self._anthropic_version = anthropic_version

    def chat_completions_create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int | None = 800,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        del response_format  # Intentionally accepted for OpenAI-compat call sites.

        system_parts: list[str] = []
        anthropic_messages: list[dict[str, Any]] = []
        for m in messages:
            role = str(m.get("role", "")).strip().lower()
            content = str(m.get("content", ""))
            if role == "system":
                if content.strip():
                    system_parts.append(content.strip())
                continue
            if role not in {"user", "assistant"}:
                continue
            anthropic_messages.append({"role": role, "content": content})

        payload: dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": int(max_tokens or 800),
            "temperature": temperature,
        }
        system_prompt = "\n\n".join(system_parts).strip()
        if system_prompt:
            payload["system"] = system_prompt

        url = f"{self._base_url}/messages"
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
            "anthropic-version": self._anthropic_version,
        }
        resp_data = _http_post_json(url=url, headers=headers, payload=payload, timeout_s=self._timeout_s)

        content_texts: list[str] = []
        content_blocks = resp_data.get("content")
        if isinstance(content_blocks, list):
            for block in content_blocks:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and isinstance(block.get("text"), str):
                    content_texts.append(block["text"])
        text = "\n".join(content_texts).strip()
        if not text and isinstance(resp_data.get("completion"), str):
            text = resp_data["completion"].strip()

        return {"choices": [{"message": {"content": text}}], "raw": resp_data}


class GoogleClient:
    def __init__(self, base_url: str, api_key: str, timeout_s: int = 60):
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
        del response_format  # Intentionally accepted for OpenAI-compat call sites.

        system_parts: list[str] = []
        contents: list[dict[str, Any]] = []
        for m in messages:
            role = str(m.get("role", "")).strip().lower()
            content = str(m.get("content", ""))
            if role == "system":
                if content.strip():
                    system_parts.append(content.strip())
                continue
            if role == "assistant":
                role = "model"
            if role not in {"user", "model"}:
                continue
            contents.append({"role": role, "parts": [{"text": content}]})

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": int(max_tokens or 800)},
        }
        system_prompt = "\n\n".join(system_parts).strip()
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        qs = urlencode({"key": self._api_key}) if self._api_key else ""
        url = f"{self._base_url}/models/{model}:generateContent"
        if qs:
            url = f"{url}?{qs}"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        resp_data = _http_post_json(url=url, headers=headers, payload=payload, timeout_s=self._timeout_s)

        # Google response shape: candidates[0].content.parts[].text
        text_parts: list[str] = []
        candidates = resp_data.get("candidates")
        if isinstance(candidates, list) and candidates:
            cand0 = candidates[0] if isinstance(candidates[0], dict) else {}
            content = cand0.get("content") if isinstance(cand0, dict) else None
            if isinstance(content, dict):
                parts = content.get("parts")
                if isinstance(parts, list):
                    for p in parts:
                        if isinstance(p, dict) and isinstance(p.get("text"), str):
                            text_parts.append(p["text"])
        text = "\n".join(text_parts).strip()

        return {"choices": [{"message": {"content": text}}], "raw": resp_data}


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

    # Try fenced code blocks: ```json ... ```
    fence = "```"
    if fence in text:
        parts = text.split(fence)
        for i in range(1, len(parts), 2):
            candidate = parts[i].strip()
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("{") and candidate.endswith("}"):
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue

    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    escape = False
    end: int | None = None
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
            continue
        if ch == "{":
            depth += 1
            continue
        if ch == "}":
            depth -= 1
            if depth == 0:
                end = idx + 1
                break
            continue

    if end is None or depth != 0:
        return None
    candidate = text[start:end].strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def chat_json(
    client: ChatClient,
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
