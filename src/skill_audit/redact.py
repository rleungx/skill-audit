from __future__ import annotations

import re

_REDACTION_RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z0-9 ]*PRIVATE KEY-----"),
        "[REDACTED:PRIVATE_KEY_BLOCK]",
    ),
    (re.compile(r"\bsk-[A-Za-z0-9-]{10,}\b"), "sk-[REDACTED]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AKIA[REDACTED]"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "AIza[REDACTED]"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._-]{20,}\b"), "Bearer [REDACTED]"),
    (re.compile(r"(?i)\bghp_[A-Za-z0-9]{20,}\b"), "ghp_[REDACTED]"),
    (re.compile(r"(?i)\bxox[baprs]-[0-9A-Za-z-]{10,}\b"), "xox-[REDACTED]"),
    (
        re.compile(r"(?i)\b(api_key|apikey|key|token)=([A-Za-z0-9._-]{8,})\b"),
        r"\1=[REDACTED]",
    ),
    (
        re.compile(r"(?i)\b(authorization:\s*bearer)\s+[A-Za-z0-9._-]{20,}\b"),
        r"\1 [REDACTED]",
    ),
]


def redact_text(text: str) -> str:
    out = text
    for pattern, replacement in _REDACTION_RULES:
        out = pattern.sub(replacement, out)
    return out

