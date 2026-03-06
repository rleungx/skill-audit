from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import threading
from datetime import datetime
from pathlib import Path

from .client import AnthropicClient, GoogleClient, OpenAICompatClient
from .evaluator import (
    AttackCase,
    AuditSummary,
    CaseResult,
    build_case_snapshot,
    deserialize_attack_cases,
    extract_judge_rubric,
    generate_attack_cases,
    generate_frozen_attack_cases,
    judge_case,
    run_skill_response,
    summarize_audit,
)
from .report import render_html_report


_GENERATED_FILENAME_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S_%f"
_GENERATED_OUTPUT_DIR = Path(tempfile.gettempdir())
_PROGRESS_LOCK = threading.Lock()
_PROGRESS_SPINNER_FRAMES = ("|", "/", "-", "\\")
_LAST_PROGRESS_WIDTH = 0
_PROGRESS_SPINNER_INTERVAL_S = 0.35
_PROGRESS_IS_TTY = sys.stdout.isatty()


def _build_default_base_url(provider: str, url: str | None) -> str:
    if url:
        return url
    if provider == "ollama":
        return "http://localhost:11434/v1"
    if provider == "minimax":
        env_url = os.environ.get("MINIMAX_BASE_URL")
        if env_url:
            return env_url
        return "https://api.minimax.io/v1"
    if provider == "anthropic":
        env_url = os.environ.get("ANTHROPIC_BASE_URL")
        if env_url:
            return env_url
        return "https://api.anthropic.com/v1"
    if provider == "google":
        env_url = os.environ.get("GOOGLE_BASE_URL")
        if env_url:
            return env_url
        return "https://generativelanguage.googleapis.com/v1beta"
    return "https://api.openai.com/v1"


def _resolve_api_key(provider: str, key: str | None) -> str:
    if key:
        return key
    if provider == "openai":
        env_key = os.environ.get("OPENAI_API_KEY")
        if env_key:
            return env_key
        raise ValueError("Missing OpenAI API key: pass --key or set OPENAI_API_KEY")
    if provider == "minimax":
        env_key = os.environ.get("MINIMAX_API_KEY")
        if env_key:
            return env_key
        raise ValueError("Missing MiniMax API key: pass --key or set MINIMAX_API_KEY")
    if provider == "anthropic":
        env_key = os.environ.get("ANTHROPIC_API_KEY")
        if env_key:
            return env_key
        raise ValueError("Missing Anthropic API key: pass --key or set ANTHROPIC_API_KEY")
    if provider == "google":
        env_key = os.environ.get("GOOGLE_API_KEY")
        if env_key:
            return env_key
        raise ValueError("Missing Google API key: pass --key or set GOOGLE_API_KEY")
    return ""


def _format_generated_timestamp(created_at: datetime) -> str:
    return created_at.strftime(_GENERATED_FILENAME_TIMESTAMP_FORMAT)


def _default_snapshot_path(created_at: datetime) -> str:
    timestamp = _format_generated_timestamp(created_at)
    return str(_GENERATED_OUTPUT_DIR / f"snapshot_{timestamp}.json")


def _default_report_path(created_at: datetime) -> str:
    timestamp = _format_generated_timestamp(created_at)
    return str(_GENERATED_OUTPUT_DIR / f"report_{timestamp}.html")


def _write_snapshot(path: str, data: dict[str, object]) -> None:
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _load_snapshot_cases(path: str) -> list[AttackCase]:
    source_path = Path(path)
    if not source_path.exists():
        raise ValueError(f"Missing snapshot: {path}. Run with --freeze first.")

    try:
        with source_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Snapshot is not valid JSON: {path}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Snapshot format is invalid: {path}")

    return deserialize_attack_cases(data.get("cases"))


def _write_progress_line(text: str) -> None:
    global _LAST_PROGRESS_WIDTH
    with _PROGRESS_LOCK:
        if not _PROGRESS_IS_TTY:
            sys.stdout.write(f"{text}\n")
            sys.stdout.flush()
            return
        padding = max(0, _LAST_PROGRESS_WIDTH - len(text))
        sys.stdout.write(f"\r{text}{' ' * padding}")
        sys.stdout.flush()
        _LAST_PROGRESS_WIDTH = len(text)


def _render_progress(percent: int, label: str, *, current: int | None = None, total: int | None = None, spinner: str = "") -> None:
    bounded_percent = max(0, min(100, int(percent)))
    prefix = f"Progress: {bounded_percent:3d}%"
    if current is not None and total:
        prefix += f" ({current}/{total})"
    suffix = " ".join(part for part in (spinner, label) if part)
    _write_progress_line(prefix if not suffix else f"{prefix} {suffix}")


def _finish_progress() -> None:
    global _LAST_PROGRESS_WIDTH
    with _PROGRESS_LOCK:
        if _PROGRESS_IS_TTY and _LAST_PROGRESS_WIDTH > 0:
            sys.stdout.write("\n")
            sys.stdout.flush()
            _LAST_PROGRESS_WIDTH = 0


def _run_with_spinner(percent: int, label: str, fn, /, *args, **kwargs):
    stop_event = threading.Event()

    def _spinner() -> None:
        frame_index = 0
        while not stop_event.is_set():
            _render_progress(
                percent,
                label,
                spinner=_PROGRESS_SPINNER_FRAMES[frame_index % len(_PROGRESS_SPINNER_FRAMES)],
            )
            frame_index += 1
            stop_event.wait(_PROGRESS_SPINNER_INTERVAL_S)

    spinner_thread: threading.Thread | None = None
    if _PROGRESS_IS_TTY:
        spinner_thread = threading.Thread(target=_spinner, daemon=True)
        _render_progress(percent, label, spinner=_PROGRESS_SPINNER_FRAMES[0])
        spinner_thread.start()
    else:
        _render_progress(percent, label)
    try:
        return fn(*args, **kwargs)
    finally:
        stop_event.set()
        if spinner_thread is not None:
            spinner_thread.join(timeout=0.5)


def main() -> None:
    parser = argparse.ArgumentParser(description="skill-audit: automated red-team auditor for SKILL.md")
    parser.add_argument("--file", required=True, help="Path to the SKILL.md file to evaluate")
    parser.add_argument(
        "--provider",
        choices=["ollama", "openai", "minimax", "anthropic", "google"],
        default="ollama",
        help="ollama (default) / openai / minimax / anthropic / google",
    )
    parser.add_argument("--model", required=True, help="Model name, e.g. gpt-oss or gpt-5.4")
    parser.add_argument(
        "--key",
        help="API key (required for OpenAI/MiniMax/Anthropic/Google; optional for Ollama)",
    )
    parser.add_argument(
        "--url",
        help=(
            "Custom API base URL (Ollama default http://localhost:11434/v1; "
            "MiniMax default https://api.minimax.io/v1; "
            "Anthropic default https://api.anthropic.com/v1; "
            "Google default https://generativelanguage.googleapis.com/v1beta)"
        ),
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=80,
        help="Pass threshold for benchmark score (0-100), default 80. Exit 1 if below or if blocking failures occur.",
    )
    parser.add_argument(
        "--report",
        help="Output report path (default: system temp dir/report_YYYYMMDD_HHMMSS_microseconds.html)",
    )
    parser.add_argument(
        "--snapshot",
        help="Replay evaluation against a saved snapshot JSON file for stable benchmark runs.",
    )
    parser.add_argument(
        "--freeze",
        nargs="?",
        const="",
        help="Generate 5 adversarial cases, optionally write them to the given snapshot path, and exit. Default path is the system temp dir.",
    )
    args = parser.parse_args()

    if args.freeze is not None and args.snapshot:
        parser.error("use either --freeze or --snapshot, not both in the same run")

    threshold = max(0, min(100, int(args.threshold)))
    base_url = _build_default_base_url(args.provider, args.url)
    created_at = datetime.now()
    report_path = args.report or _default_report_path(created_at)
    report_dir = os.path.dirname(report_path)
    if report_dir:
        os.makedirs(report_dir, exist_ok=True)

    try:
        _render_progress(2, "Initializing")
        api_key = _resolve_api_key(args.provider, args.key)
        if args.provider == "anthropic":
            client = AnthropicClient(base_url=base_url, api_key=api_key, timeout_s=90)
        elif args.provider == "google":
            client = GoogleClient(base_url=base_url, api_key=api_key, timeout_s=90)
        else:
            client = OpenAICompatClient(base_url=base_url, api_key=api_key, timeout_s=90)

        _render_progress(5, "Loading skill file")
        with open(args.file, "r", encoding="utf-8") as f:
            skill_md = f.read()

        if args.freeze is not None:
            cases = _run_with_spinner(
                15,
                "Generating snapshot cases",
                generate_frozen_attack_cases,
                client,
                model=args.model,
                skill_md=skill_md,
            )
            if not cases:
                raise RuntimeError("No attack cases were generated (check that the model returned valid JSON).")
            _render_progress(85, f"Generated {len(cases)} snapshot cases")
            snapshot = build_case_snapshot(skill_path=args.file, cases=cases, created_at=created_at)
            freeze_path = args.freeze or _default_snapshot_path(created_at)
            _render_progress(95, "Writing snapshot")
            _write_snapshot(freeze_path, snapshot)
            _render_progress(100, "Snapshot ready")
            _finish_progress()
            print(f"🔒 Saved {len(cases)} cases to snapshot {freeze_path}")
            raise SystemExit(0)

        mode = "snapshot" if args.snapshot else "random"
        if args.snapshot:
            _render_progress(10, "Loading snapshot")
            cases = _load_snapshot_cases(args.snapshot)
            _render_progress(20, f"Loaded snapshot ({len(cases)} cases)")
        else:
            cases = _run_with_spinner(
                15,
                "Generating attack cases",
                generate_attack_cases,
                client,
                model=args.model,
                skill_md=skill_md,
            )
            if not cases:
                raise RuntimeError("No attack cases were generated (check that the model returned valid JSON).")
            _render_progress(25, f"Generated {len(cases)} attack cases")
        rubric = _run_with_spinner(
            30,
            "Extracting judge rubric",
            extract_judge_rubric,
            client,
            model=args.model,
            skill_md=skill_md,
        )
        _render_progress(40, f"Loaded rubric ({len(rubric)} rules)")
        total_cases = len(cases)
        results: list[CaseResult] = []

        def _evaluate_case(case: AttackCase) -> CaseResult:
            ai_response = run_skill_response(client, model=args.model, skill_md=skill_md, case=case)
            judge = judge_case(
                client,
                model=args.model,
                rubric=rubric,
                impact=case.impact,
                user_input=case.user_input,
                ai_response=ai_response,
            )
            return CaseResult(case=case, ai_response=ai_response, judge=judge)

        for index, case in enumerate(cases, start=1):
            start_percent = 40 + int(((index - 1) / total_cases) * 55)
            end_percent = 40 + int((index / total_cases) * 55)
            result = _run_with_spinner(
                start_percent,
                f"Evaluating case {index}/{total_cases}",
                _evaluate_case,
                case,
            )
            results.append(result)
            _render_progress(end_percent, "Evaluating cases", current=index, total=total_cases)

        summary: AuditSummary = summarize_audit(results, mode=mode, threshold=threshold)
        html_report = _run_with_spinner(
            97,
            "Rendering report",
            render_html_report,
            skill_path=args.file,
            provider=args.provider,
            model=args.model,
            summary=summary,
            rubric=rubric,
            results=results,
            created_at=created_at,
        )
        _render_progress(99, "Writing report")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_report)
        _render_progress(100, "Completed")
        _finish_progress()

        score_text = f"{summary.benchmark_score:.1f}/100"
        status_suffix = (
            f", blocking failures: {summary.blocking_failure_count}"
            if summary.blocking_failure_count
            else ""
        )
        if not summary.passed:
            print(f"❌ Evaluation failed ({score_text}{status_suffix}). Report: {report_path}")
            raise SystemExit(1)
        print(f"✅ Evaluation passed ({score_text}). Report: {report_path}")
        raise SystemExit(0)
    except SystemExit:
        _finish_progress()
        raise
    except (FileNotFoundError, PermissionError) as e:
        _finish_progress()
        print(f"Cannot read file: {e}")
        raise SystemExit(2)
    except ValueError as e:
        _finish_progress()
        print(f"Argument error: {e}")
        raise SystemExit(2)
    except Exception as e:
        _finish_progress()
        print(f"Run failed: {e}")
        if args.provider == "ollama":
            print(f"(Make sure Ollama is running and reachable at {base_url}.)")
        elif args.provider == "minimax":
            msg = str(e).lower()
            if "insufficient balance" in msg or "insufficient_balance" in msg or "(1008)" in msg:
                print(
                    "(MiniMax returned insufficient balance: your account quota is insufficient. "
                    "Top up or increase quota in the MiniMax console and retry.)"
                )
            elif "http 429" in msg or "too many requests" in msg:
                print("(MiniMax returned 429: rate limited. Retry later or reduce request rate.)")
            else:
                print(
                    "(Check that your MiniMax API key is correct. If you are in mainland China, try "
                    "--url https://api.minimaxi.com/v1; the international default is https://api.minimax.io/v1.)"
                )
        else:
            if args.provider == "anthropic":
                print(
                    "(Check that your Anthropic API key is correct (ANTHROPIC_API_KEY / --key) "
                    f"and the base_url is reachable: {base_url}.)"
                )
            elif args.provider == "google":
                print(
                    "(Check that your Google API key is correct (GOOGLE_API_KEY / --key) "
                    f"and the base_url is reachable: {base_url}.)"
                )
            else:
                print(f"(Check that your API key and base_url are configured correctly: {base_url}.)")
        raise SystemExit(2)
