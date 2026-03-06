from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path

from .evaluator import AttackCase, deserialize_attack_cases


GENERATED_FILENAME_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S_%f"
GENERATED_OUTPUT_DIR = Path(tempfile.gettempdir())


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


def write_snapshot(path: str, data: dict[str, object]) -> None:
    target_path = ensure_parent_dir(path)
    with target_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def write_text_file(path: str, content: str) -> None:
    target_path = ensure_parent_dir(path)
    with target_path.open("w", encoding="utf-8") as file:
        file.write(content)


def load_snapshot_cases(path: str) -> list[AttackCase]:
    source_path = Path(path)
    if not source_path.exists():
        raise ValueError(f"Missing snapshot: {path}. Run with --freeze first.")

    try:
        with source_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Snapshot is not valid JSON: {path}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Snapshot format is invalid: {path}")

    return deserialize_attack_cases(data.get("cases"))
