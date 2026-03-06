from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Sequence

from .evaluator import (
    AttackCase,
    AuditSummary,
    CaseResult,
    build_case_snapshot,
    extract_judge_rubric,
    generate_attack_cases,
    generate_frozen_attack_cases,
    judge_case,
    run_skill_response,
    summarize_audit,
)
from .progress import ProgressReporter
from .providers import (
    PROVIDER_CHOICES,
    PROVIDER_HELP_TEXT,
    build_client,
    format_runtime_hint,
    resolve_api_key,
    resolve_base_url,
)
from .report import render_html_report
from .storage import (
    default_report_path,
    default_snapshot_path,
    load_snapshot_cases,
    write_snapshot,
    write_text_file,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="skill-audit: automated red-team auditor for SKILL.md")
    parser.add_argument("--file", required=True, help="Path to the SKILL.md file to evaluate")
    parser.add_argument(
        "--provider",
        choices=PROVIDER_CHOICES,
        default="ollama",
        help=PROVIDER_HELP_TEXT,
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
    return parser


def _evaluate_case(*, client, model: str, skill_md: str, rubric, case: AttackCase) -> CaseResult:
    ai_response = run_skill_response(client, model=model, skill_md=skill_md, case=case)
    judge = judge_case(
        client,
        model=model,
        rubric=rubric,
        impact=case.impact,
        user_input=case.user_input,
        ai_response=ai_response,
    )
    return CaseResult(case=case, ai_response=ai_response, judge=judge)


def main(argv: Sequence[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    progress = ProgressReporter()

    if args.freeze is not None and args.snapshot:
        parser.error("use either --freeze or --snapshot, not both in the same run")

    threshold = max(0, min(100, int(args.threshold)))
    base_url = resolve_base_url(args.provider, args.url)
    created_at = datetime.now()

    try:
        progress.render(2, "Initializing")
        api_key = resolve_api_key(args.provider, args.key)
        client = build_client(args.provider, base_url=base_url, api_key=api_key, timeout_s=90)

        progress.render(5, "Loading skill file")
        skill_md = Path(args.file).read_text(encoding="utf-8")

        if args.freeze is not None:
            cases = progress.run_with_spinner(
                15,
                "Generating snapshot cases",
                generate_frozen_attack_cases,
                client,
                model=args.model,
                skill_md=skill_md,
            )
            if not cases:
                raise RuntimeError("No attack cases were generated (check that the model returned valid JSON).")
            progress.render(85, f"Generated {len(cases)} snapshot cases")
            snapshot = build_case_snapshot(skill_path=args.file, cases=cases, created_at=created_at)
            freeze_path = args.freeze or default_snapshot_path(created_at)
            progress.render(95, "Writing snapshot")
            write_snapshot(freeze_path, snapshot)
            progress.render(100, "Snapshot ready")
            progress.finish()
            print(f"🔒 Saved {len(cases)} cases to snapshot {freeze_path}")
            raise SystemExit(0)

        mode = "snapshot" if args.snapshot else "random"
        if args.snapshot:
            progress.render(10, "Loading snapshot")
            cases = load_snapshot_cases(args.snapshot)
            progress.render(20, f"Loaded snapshot ({len(cases)} cases)")
        else:
            cases = progress.run_with_spinner(
                15,
                "Generating attack cases",
                generate_attack_cases,
                client,
                model=args.model,
                skill_md=skill_md,
            )
            if not cases:
                raise RuntimeError("No attack cases were generated (check that the model returned valid JSON).")
            progress.render(25, f"Generated {len(cases)} attack cases")
        rubric = progress.run_with_spinner(
            30,
            "Extracting judge rubric",
            extract_judge_rubric,
            client,
            model=args.model,
            skill_md=skill_md,
        )
        progress.render(40, f"Loaded rubric ({len(rubric)} rules)")
        total_cases = len(cases)
        results: list[CaseResult] = []

        for index, case in enumerate(cases, start=1):
            start_percent = 40 + int(((index - 1) / total_cases) * 55)
            end_percent = 40 + int((index / total_cases) * 55)
            result = progress.run_with_spinner(
                start_percent,
                f"Evaluating case {index}/{total_cases}",
                _evaluate_case,
                client=client,
                model=args.model,
                skill_md=skill_md,
                rubric=rubric,
                case=case,
            )
            results.append(result)
            progress.render(end_percent, "Evaluating cases", current=index, total=total_cases)

        summary: AuditSummary = summarize_audit(results, mode=mode, threshold=threshold)
        report_path = args.report or default_report_path(created_at)
        html_report = progress.run_with_spinner(
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
        progress.render(99, "Writing report")
        write_text_file(report_path, html_report)
        progress.render(100, "Completed")
        progress.finish()

        score_text = f"{summary.benchmark_score:.1f}/100"
        status_suffix = (
            f", blocking failures: {summary.blocking_failure_count}"
            if summary.blocking_failure_count
            else ""
        )
        if not summary.passed:
            print(f"Evaluation failed ({score_text}{status_suffix}). Report: {report_path}")
            raise SystemExit(1)
        print(f"Evaluation passed ({score_text}). Report: {report_path}")
        raise SystemExit(0)
    except SystemExit:
        progress.finish()
        raise
    except (FileNotFoundError, PermissionError) as e:
        progress.finish()
        print(f"Cannot read file: {e}")
        raise SystemExit(2)
    except ValueError as e:
        progress.finish()
        print(f"Argument error: {e}")
        raise SystemExit(2)
    except Exception as e:
        progress.finish()
        print(f"Run failed: {e}")
        hint = format_runtime_hint(args.provider, base_url=base_url, error=e)
        if hint:
            print(hint)
        raise SystemExit(2)
