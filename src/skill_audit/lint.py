from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class LintFinding:
    code: str
    severity: str  # "critical" | "high" | "medium" | "low"
    message: str
    evidence: str | None = None


_SECRET_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "SKILL_LINT_SECRET_PRIVATE_KEY",
        "critical",
        re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    ),
    (
        "SKILL_LINT_SECRET_OPENAI",
        "critical",
        re.compile(r"(?i)\bsk-[a-z0-9]{20,}\b"),
    ),
    (
        "SKILL_LINT_SECRET_AWS_ACCESS_KEY_ID",
        "critical",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "SKILL_LINT_SECRET_GITHUB_TOKEN",
        "critical",
        re.compile(r"(?i)\bghp_[a-z0-9]{20,}\b"),
    ),
    (
        "SKILL_LINT_SECRET_JWT",
        "high",
        re.compile(r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b"),
    ),
]

_PROMPT_INTEGRITY_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "SKILL_LINT_PROMPT_LEAKAGE",
        "critical",
        re.compile(r"(?is)\b(reveal|print|show|leak)\b.{0,80}\b(system prompt|developer message|hidden instructions)\b"),
    ),
    (
        "SKILL_LINT_INJECTION_PHRASE",
        "high",
        re.compile(r"(?is)\b(ignore|disregard)\b.{0,40}\b(previous|earlier|above)\b.{0,20}\b(instructions|rules)\b"),
    ),
    (
        "SKILL_LINT_OVERCOMPLIANCE",
        "high",
        re.compile(r"(?is)\b(always comply|never refuse|no matter what|do anything|without question)\b"),
    ),
]

_TOOL_RISK_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    ("SKILL_LINT_TOOL_SUDO", "high", re.compile(r"(?i)\bsudo\b")),
    ("SKILL_LINT_TOOL_RM_RF", "high", re.compile(r"(?i)\brm\s+-rf\b")),
    ("SKILL_LINT_TOOL_POWERSHELL", "medium", re.compile(r"(?i)\bpowershell\b")),
    ("SKILL_LINT_TOOL_BASH", "medium", re.compile(r"(?i)\b(bash|zsh|sh)\b")),
    ("SKILL_LINT_TOOL_CURL_WGET", "medium", re.compile(r"(?i)\b(curl|wget)\b")),
]


def _truncate_evidence(text: str, *, limit: int = 120) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def lint_skill_document(skill_md: str) -> list[LintFinding]:
    findings: list[LintFinding] = []
    seen: set[str] = set()

    def add(code: str, severity: str, message: str, evidence: str | None) -> None:
        if code in seen:
            return
        seen.add(code)
        findings.append(
            LintFinding(
                code=code,
                severity=severity,
                message=message,
                evidence=_truncate_evidence(evidence) if evidence else None,
            )
        )

    for code, severity, pattern in _SECRET_PATTERNS:
        match = pattern.search(skill_md)
        if not match:
            continue
        add(code, severity, "Potential secret material detected in skill document.", match.group(0))

    for code, severity, pattern in _PROMPT_INTEGRITY_PATTERNS:
        match = pattern.search(skill_md)
        if not match:
            continue
        add(code, severity, "Potential prompt-integrity weakness detected in skill document.", match.group(0))

    for code, severity, pattern in _TOOL_RISK_PATTERNS:
        match = pattern.search(skill_md)
        if not match:
            continue
        add(code, severity, "Skill document references potentially dangerous tooling or commands. Ensure strict gating/confirmation.", match.group(0))

    severity_rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    findings.sort(key=lambda f: (severity_rank.get(f.severity, -1), f.code), reverse=True)
    return findings

