from __future__ import annotations

from .models import AttackTurn


def normalize_attack_turns(
    raw_turns: object,
    *,
    max_turn_chars: int = 2000,
    max_turns_per_case: int = 3,
) -> list[AttackTurn]:
    if not isinstance(raw_turns, list):
        return []

    normalized_turns: list[AttackTurn] = []
    for turn in raw_turns:
        text = str(turn).strip()
        if not text:
            continue
        normalized_turns.append(AttackTurn(text[:max_turn_chars]))
        if len(normalized_turns) >= max_turns_per_case:
            break
    return normalized_turns
