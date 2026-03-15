from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import AttackCase, RubricItem
from .turns import normalize_attack_turns


def serialize_rubric_items(rubric: list[RubricItem]) -> list[dict[str, str]]:
    return [{"rule": item.rule, "level": item.level} for item in rubric]


def deserialize_rubric_items(data: object) -> list[RubricItem]:
    def normalize_level(raw: object) -> str:
        level = str(raw or "required").strip().lower()
        if level in ("required", "hard", "must"):
            return "required"
        if level in ("advisory", "soft", "should", "recommended"):
            return "advisory"
        return "required"

    if not isinstance(data, list):
        return []
    return [
        RubricItem(str(item.get("rule", "")), normalize_level(item.get("level", "required")))
        for item in data
        if isinstance(item, dict)
    ]


def serialize_attack_cases(cases: list[AttackCase]) -> list[dict[str, object]]:
    return [
        {
            "scenario": case.scenario,
            "risk_category": case.risk_category,
            "impact": case.impact,
            "turns": [turn.user_input for turn in case.turns],
        }
        for case in cases
    ]


def deserialize_attack_cases(data: Any) -> list[AttackCase]:
    if not isinstance(data, list):
        return []
    cases: list[AttackCase] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        turns = normalize_attack_turns(item.get("turns"))
        if not turns:
            continue
        cases.append(
            AttackCase(
                str(item.get("scenario", "")),
                turns,
                str(item.get("risk_category", "unknown")),
                str(item.get("impact", "medium")),
            )
        )
    return cases


def build_case_snapshot(*, skill_path: str, cases: list[AttackCase], rubric: list[RubricItem]) -> dict[str, Any]:
    return {
        "version": 4,
        "metadata": {
            "taxonomy": "v2-security",
            "created_at": datetime.now().isoformat(),
            "skill_file": skill_path,
        },
        "rubric": serialize_rubric_items(rubric),
        "cases": serialize_attack_cases(cases),
    }
