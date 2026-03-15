from __future__ import annotations

from typing import Any

from .attack_generation import generate_attack_cases as _generate_attack_cases
from .attack_generation import generate_frozen_attack_cases as _generate_frozen_attack_cases
from .client import ChatClient, chat_json, extract_message_content
from .judging import judge_case as _judge_case
from .lint import LintFinding
from .models import AttackCase, AuditSummary, CaseResult, JudgeResult, RubricItem
from .models import AttackTurn as _AttackTurn
from .prompts import RUBRIC_EXTRACT_SYSTEM_PROMPT, RUBRIC_EXTRACT_USER_PROMPT_TEMPLATE, SIMULATE_SYSTEM_TEMPLATE
from .serialization import deserialize_attack_cases as _deserialize_attack_cases
from .serialization import deserialize_rubric_items
from .summary import summarize_audit as _summarize_audit

# DETECTOR VERSIONING
DETECTOR_VERSION = "1.7.0-security"
AttackTurn = _AttackTurn

def run_skill_response(client: ChatClient, *, model: str, skill_md: str, case: AttackCase) -> list[str]:
    history = [{"role": "system", "content": SIMULATE_SYSTEM_TEMPLATE.format(skill_md=skill_md)}]
    responses = []
    for turn in case.turns:
        history.append({"role": "user", "content": turn.user_input})
        content = extract_message_content(client.chat_completions_create(model=model, messages=history, temperature=0.0)).strip()
        responses.append(content)
        history.append({"role": "assistant", "content": content})
    return responses


def summarize_audit(
    results: list[CaseResult],
    *,
    threshold: int,
    lint_findings: list[LintFinding] | None = None,
    fail_on_lint: bool = False,
) -> AuditSummary:
    return _summarize_audit(
        results,
        threshold=threshold,
        lint_findings=lint_findings,
        fail_on_lint=fail_on_lint,
    )

def extract_judge_rubric(client: ChatClient, *, model: str, skill_md: str) -> list[RubricItem]:
    data = chat_json(
        client,
        model=model,
        messages=[
            {"role": "system", "content": RUBRIC_EXTRACT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": RUBRIC_EXTRACT_USER_PROMPT_TEMPLATE.format(skill_content=skill_md),
            },
        ],
        temperature=0.0,
    )
    rubric = deserialize_rubric_items(data.get("rubric", []))
    if not rubric:
        raise RuntimeError("Rubric extraction returned empty rubric.")
    return rubric


def deserialize_attack_cases(data: Any) -> list[AttackCase]:
    return _deserialize_attack_cases(data)


def generate_attack_cases(client: ChatClient, *, model: str, skill_md: str) -> list[AttackCase]:
    return _generate_attack_cases(client, model=model, skill_md=skill_md)


def generate_frozen_attack_cases(client: ChatClient, *, model: str, skill_md: str) -> list[AttackCase]:
    return _generate_frozen_attack_cases(client, model=model, skill_md=skill_md)


def judge_case(
    client: ChatClient,
    *,
    model: str,
    rubric: list[RubricItem],
    case: AttackCase,
    responses: list[str],
    skill_md: str,
) -> JudgeResult:
    return _judge_case(
        client,
        model=model,
        rubric=rubric,
        case=case,
        responses=responses,
        skill_md=skill_md,
    )
