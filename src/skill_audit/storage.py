from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .evaluator import DETECTOR_VERSION
from .models import AttackCase, RubricItem
from .serialization import (
    deserialize_attack_cases,
    deserialize_rubric_items,
    serialize_attack_cases,
    serialize_rubric_items,
)

GENERATED_FILENAME_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S_%f"
GENERATED_OUTPUT_DIR = Path(tempfile.gettempdir())
SNAPSHOT_VERSION = 4
# Default to a writable temp location; callers can override this explicitly.
CACHE_DIR = Path(
    os.environ.get(
        "SKILL_AUDIT_CACHE_DIR",
        str(GENERATED_OUTPUT_DIR / "skill_audit-cache"),
    )
)


def format_generated_timestamp(created_at: datetime) -> str:
    return created_at.strftime(GENERATED_FILENAME_TIMESTAMP_FORMAT)


def default_snapshot_path(created_at: datetime) -> str:
    timestamp = format_generated_timestamp(created_at)
    return str(GENERATED_OUTPUT_DIR / f"snapshot_{timestamp}.json")


def default_report_path(created_at: datetime) -> str:
    timestamp = format_generated_timestamp(created_at)
    return str(GENERATED_OUTPUT_DIR / f"report_{timestamp}.html")


def ensure_parent_dir(path: str | Path) -> Path:
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    return target_path


def write_snapshot(path: str, data: dict[str, Any]) -> None:
    target_path = ensure_parent_dir(path)
    with target_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def write_text_file(path: str, content: str) -> None:
    target_path = ensure_parent_dir(path)
    with target_path.open("w", encoding="utf-8") as file:
        file.write(content)


def load_snapshot(path: str) -> dict[str, Any]:
    source_path = Path(path)
    if not source_path.exists():
        raise ValueError(f"Missing snapshot: {path}")
    with source_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid snapshot format: {path}")
    if data.get("version") != SNAPSHOT_VERSION:
        raise ValueError(
            f"Unsupported snapshot version: expected {SNAPSHOT_VERSION}, got {data.get('version')!r}"
        )
    raw_cases = data.get("cases", [])
    raw_rubric = data.get("rubric", [])
    raw_metadata = data.get("metadata", {})
    if not isinstance(raw_cases, list):
        raise ValueError("Invalid snapshot: 'cases' must be a list")
    if not isinstance(raw_rubric, list):
        raise ValueError("Invalid snapshot: 'rubric' must be a list")
    if not isinstance(raw_metadata, dict):
        raise ValueError("Invalid snapshot: 'metadata' must be an object")

    return {
        "cases": deserialize_attack_cases(raw_cases),
        "rubric": deserialize_rubric_items(raw_rubric),
        "metadata": raw_metadata,
    }


def get_complex_cache_key(skill_content: str, target_model: str, attacker_model: str, judge_model: str) -> str:
    # Key includes content, all models, and current detector/taxonomy version
    components = [skill_content, target_model, attacker_model, judge_model, DETECTOR_VERSION, "v2-taxonomy"]
    combined = "|".join(components)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def load_cache(skill_content: str, target_model: str, attacker_model: str, judge_model: str) -> dict[str, Any] | None:
    cache_key = get_complex_cache_key(skill_content, target_model, attacker_model, judge_model)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            with cache_file.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return None
    return None


def save_cache(
    skill_content: str,
    target_model: str,
    attacker_model: str,
    judge_model: str,
    rubric: list[RubricItem],
    cases: list[AttackCase],
) -> None:
    cache_key = get_complex_cache_key(skill_content, target_model, attacker_model, judge_model)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    data = {
        "rubric": serialize_rubric_items(rubric),
        "cases": serialize_attack_cases(cases),
    }
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with cache_file.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False)
    except OSError:
        # Cache writes are optional; an unwritable cache directory should not fail the audit.
        return
