from __future__ import annotations

from typing import Any

from .client import ChatClient, chat_json
from .models import AttackCase
from .prompts import ATTACKER_SYSTEM_PROMPT, ATTACKER_USER_PROMPT_TEMPLATE, RISK_TAXONOMY
from .turns import normalize_attack_turns

_MAX_TURNS_PER_CASE = 3
_MAX_TURN_CHARS = 2000
_MAX_SCENARIO_CHARS = 240
_MAX_CASES_PER_RISK = 4


def _normalize_attack_case(raw_case: dict[str, Any], risk_category: str) -> AttackCase | None:
    scenario = str(raw_case.get("scenario", "")).strip()
    if len(scenario) > _MAX_SCENARIO_CHARS:
        scenario = scenario[:_MAX_SCENARIO_CHARS].rstrip()
    turns = normalize_attack_turns(
        raw_case.get("turns"),
        max_turn_chars=_MAX_TURN_CHARS,
        max_turns_per_case=_MAX_TURNS_PER_CASE,
    )
    if not scenario or not turns:
        return None
    return AttackCase(
        scenario,
        turns,
        risk_category,
        str(raw_case.get("impact", "medium")),
    )


def _request_attack_cases_for_risk(
    client: ChatClient,
    *,
    model: str,
    skill_md: str,
    risk_category: str,
    risk_description: str,
) -> list[dict[str, Any]]:
    response_data = chat_json(
        client,
        model=model,
        messages=[
            {"role": "system", "content": ATTACKER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": ATTACKER_USER_PROMPT_TEMPLATE.format(
                    risk_category=risk_category,
                    risk_description=risk_description,
                    skill_md=skill_md,
                ),
            },
        ],
    )
    raw_cases = response_data.get("cases", [])
    if not isinstance(raw_cases, list):
        raise ValueError("invalid response shape")
    return [item for item in raw_cases if isinstance(item, dict)]


def _select_attack_cases(
    cases_by_risk: dict[str, list[AttackCase]],
    *,
    max_total: int = 20,
    max_per_risk: int = 2,
) -> list[AttackCase]:
    selected: list[AttackCase] = []
    for offset in range(max_per_risk):
        for risk_category in RISK_TAXONOMY:
            if len(selected) >= max_total:
                return selected
            risk_cases = cases_by_risk.get(risk_category, [])
            if offset < len(risk_cases):
                selected.append(risk_cases[offset])

    for risk_category in RISK_TAXONOMY:
        for case in cases_by_risk.get(risk_category, [])[max_per_risk:]:
            if len(selected) >= max_total:
                return selected
            selected.append(case)
    return selected


def generate_attack_cases(client: ChatClient, *, model: str, skill_md: str) -> list[AttackCase]:
    cases_by_risk: dict[str, list[AttackCase]] = {risk: [] for risk in RISK_TAXONOMY}
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    generation_failures: list[str] = []
    for risk_category, risk_description in RISK_TAXONOMY.items():
        try:
            raw_cases = _request_attack_cases_for_risk(
                client,
                model=model,
                skill_md=skill_md,
                risk_category=risk_category,
                risk_description=risk_description,
            )
            for raw_case in raw_cases:
                case = _normalize_attack_case(raw_case, risk_category)
                if case is None:
                    continue
                turns_text = tuple(turn.user_input for turn in case.turns)
                stable_key = (risk_category, case.scenario, turns_text)
                if stable_key in seen:
                    continue
                seen.add(stable_key)
                cases_by_risk[risk_category].append(case)
                if len(cases_by_risk[risk_category]) >= _MAX_CASES_PER_RISK:
                    break
        except Exception as error:
            generation_failures.append(f"{risk_category}: {error}")

    selected = _select_attack_cases(cases_by_risk)
    if not selected:
        details = "; ".join(generation_failures[:3]) if generation_failures else "no valid cases returned"
        raise RuntimeError(f"Attack generation failed: {details}")
    return selected


def generate_frozen_attack_cases(client: ChatClient, *, model: str, skill_md: str) -> list[AttackCase]:
    return generate_attack_cases(client, model=model, skill_md=skill_md)
