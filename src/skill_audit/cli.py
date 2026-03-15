from __future__ import annotations

import argparse
import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import Sequence

from .api import (
    AttackCase,
    AuditSummary,
    CaseResult,
    RubricItem,
    build_case_snapshot,
    deserialize_attack_cases,
    deserialize_rubric_items,
    extract_judge_rubric,
    generate_attack_cases,
    generate_frozen_attack_cases,
    judge_case,
    run_skill_response,
    summarize_audit,
)
from .client import ChatClient
from .lint import LintFinding, lint_skill_document
from .progress import ProgressReporter
from .providers import (
    PROVIDER_CHOICES,
    build_client,
    format_runtime_hint,
    resolve_api_key,
    resolve_base_url,
)
from .redact import redact_text
from .report import render_html_report
from .storage import (
    default_report_path,
    default_snapshot_path,
    load_cache,
    load_snapshot,
    save_cache,
    write_snapshot,
    write_text_file,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="skill-audit: industrial security auditor")
    parser.add_argument("--file", required=True, help="SKILL.md path")
    parser.add_argument("--provider", choices=PROVIDER_CHOICES + ("http",), default="ollama")
    parser.add_argument("--model", required=True, help="Target model")
    parser.add_argument("--attacker-provider", choices=PROVIDER_CHOICES + ("http",))
    parser.add_argument("--attacker-model")
    parser.add_argument("--judge-provider", choices=PROVIDER_CHOICES + ("http",))
    parser.add_argument("--judge-model")
    parser.add_argument("--key")
    parser.add_argument("--url")
    parser.add_argument("--threshold", type=int, default=80)
    parser.add_argument("--report")
    parser.add_argument("--snapshot")
    parser.add_argument("--freeze", nargs="?", const="")
    parser.add_argument("--concurrency", "-j", type=int, default=1)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--no-lint", action="store_true", help="Disable static lint checks on the Skill document.")
    parser.add_argument("--fail-on-lint", action="store_true", help="Fail the audit when lint finds high/critical issues.")
    parser.add_argument("--no-redact", action="store_true", help="Do not redact suspected secrets in the HTML report (unsafe).")
    return parser


def _resolve_client(
    *,
    provider: str,
    api_key: str | None,
    base_url: str | None,
) -> ChatClient:
    return build_client(
        provider,
        base_url=resolve_base_url(provider, base_url),
        api_key=resolve_api_key(provider, api_key),
    )


def _evaluate_case(
    *,
    target_client: ChatClient,
    target_model: str,
    judge_client: ChatClient,
    judge_model: str,
    skill_md: str,
    rubric: list[RubricItem],
    case: AttackCase,
) -> CaseResult:
    responses = run_skill_response(target_client, model=target_model, skill_md=skill_md, case=case)
    judge = judge_case(
        judge_client,
        model=judge_model,
        rubric=rubric,
        case=case,
        responses=responses,
        skill_md=skill_md,
    )
    return CaseResult(case=case, ai_responses=responses, judge=judge)


def _validate_args(args: argparse.Namespace) -> None:
    if args.freeze is not None and args.snapshot:
        raise ValueError("use either --freeze or --snapshot, not both")
    if args.no_lint and args.fail_on_lint:
        raise ValueError("--fail-on-lint requires lint enabled (remove --no-lint)")
    if args.concurrency < 1:
        raise ValueError("--concurrency must be >= 1")
    if not 0 <= args.threshold <= 100:
        raise ValueError("--threshold must be between 0 and 100")


def _load_skill_and_lint(*, file_path: str, no_lint: bool) -> tuple[str, list[LintFinding]]:
    skill_md = Path(file_path).read_text(encoding="utf-8")
    lint_findings = [] if no_lint else lint_skill_document(skill_md)
    return skill_md, lint_findings


def _build_clients(args: argparse.Namespace) -> tuple[ChatClient, ChatClient, ChatClient]:
    target_provider = args.provider
    attacker_provider = args.attacker_provider or target_provider
    judge_provider = args.judge_provider or target_provider
    return (
        _resolve_client(provider=target_provider, api_key=args.key, base_url=args.url),
        _resolve_client(provider=attacker_provider, api_key=args.key, base_url=args.url),
        _resolve_client(provider=judge_provider, api_key=args.key, base_url=args.url),
    )


def _load_cases_and_rubric(
    *,
    args: argparse.Namespace,
    skill_md: str,
    attacker_client: ChatClient,
    attacker_model: str,
    judge_client: ChatClient,
    judge_model: str,
    progress: ProgressReporter,
) -> tuple[list[AttackCase], list[RubricItem]]:
    if args.snapshot:
        snapshot = load_snapshot(args.snapshot)
        progress.render(10, "Using snapshot (replay mode)")
        cases = snapshot["cases"]
        rubric = snapshot["rubric"]
        if not cases:
            raise ValueError(f"Snapshot did not contain any valid cases: {args.snapshot}")
        if not rubric:
            raise ValueError(f"Snapshot did not contain any rubric rules: {args.snapshot}")
        return cases, rubric

    cached = load_cache(skill_md, args.model, attacker_model, judge_model) if not args.no_cache else None
    if cached:
        progress.render(10, "Using cache")
        cases = deserialize_attack_cases(cached.get("cases", []))
        rubric = deserialize_rubric_items(cached.get("rubric", []))
        if not cases:
            raise ValueError("Cache did not contain any valid cases. Re-run with --no-cache to regenerate them.")
        if not rubric:
            raise ValueError("Cache did not contain any rubric rules. Re-run with --no-cache to regenerate them.")
        return cases, rubric

    cases = generate_attack_cases(attacker_client, model=attacker_model, skill_md=skill_md)
    rubric = extract_judge_rubric(judge_client, model=judge_model, skill_md=skill_md)
    if not cases:
        return cases, rubric
    if not rubric:
        return cases, rubric
    if not args.no_cache:
        save_cache(skill_md, args.model, attacker_model, judge_model, rubric, cases)
    return cases, rubric


def _run_case_evaluations(
    *,
    target_client: ChatClient,
    target_model: str,
    judge_client: ChatClient,
    judge_model: str,
    skill_md: str,
    rubric: list[RubricItem],
    cases: list[AttackCase],
    concurrency: int,
    progress: ProgressReporter,
) -> list[CaseResult]:
    total = len(cases)
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        results_by_index: list[CaseResult | None] = [None] * total
        futures = {
            executor.submit(
                _evaluate_case,
                target_client=target_client,
                target_model=target_model,
                judge_client=judge_client,
                judge_model=judge_model,
                skill_md=skill_md,
                rubric=rubric,
                case=case,
            ): index
            for index, case in enumerate(cases)
        }
        for completed_index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            case_index = futures[future]
            results_by_index[case_index] = future.result()
            progress.render(40 + int((completed_index / total) * 55), "Evaluating", current=completed_index, total=total)
    return [result for result in results_by_index if result is not None]


def _build_failure_note(summary: AuditSummary, *, fail_on_lint: bool) -> str:
    failure_notes: list[str] = []
    if summary.blocking_failure_count:
        count = summary.blocking_failure_count
        failure_notes.append(f"{count} blocking case{'s' if count != 1 else ''}")
    if fail_on_lint and summary.lint_blocking_count:
        count = summary.lint_blocking_count
        failure_notes.append(f"{count} blocking lint finding{'s' if count != 1 else ''}")
    if not failure_notes:
        failure_notes.append("Review the failing cases in the report")
    return ". ".join(failure_notes) if failure_notes else "Review the report for details"


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    try:
        _validate_args(args)
    except ValueError as error:
        print(f"Argument error: {error}. See 'skill-audit --help' for usage details.")
        raise SystemExit(2)

    progress = ProgressReporter()
    created_at = datetime.now()

    try:
        skill_md, lint_findings = _load_skill_and_lint(file_path=args.file, no_lint=args.no_lint)
        progress.render(2, "Initializing")
        target_client, attacker_client, judge_client = _build_clients(args)

        attacker_model = args.attacker_model or args.model
        judge_model = args.judge_model or args.model

        # 1. Freeze Path
        if args.freeze is not None:
            cases = generate_frozen_attack_cases(attacker_client, model=attacker_model, skill_md=skill_md)
            rubric = extract_judge_rubric(judge_client, model=judge_model, skill_md=skill_md)
            if not rubric:
                raise ValueError("No rubric rules were generated. Re-run the audit to regenerate them.")
            snapshot_path = args.freeze or default_snapshot_path(created_at)
            write_snapshot(
                snapshot_path,
                build_case_snapshot(skill_path=args.file, cases=cases, rubric=rubric),
            )
            print(f"Snapshot saved to {snapshot_path}.")
            return

        cases, rubric = _load_cases_and_rubric(
            args=args,
            skill_md=skill_md,
            attacker_client=attacker_client,
            attacker_model=attacker_model,
            judge_client=judge_client,
            judge_model=judge_model,
            progress=progress,
        )
        if not cases:
            raise ValueError("No audit cases were loaded. Re-run with a valid snapshot or regenerate cases.")
        if not rubric:
            raise ValueError("No rubric rules were loaded. Re-run the audit to regenerate them.")

        results = _run_case_evaluations(
            target_client=target_client,
            target_model=args.model,
            judge_client=judge_client,
            judge_model=judge_model,
            skill_md=skill_md,
            rubric=rubric,
            cases=cases,
            concurrency=args.concurrency,
            progress=progress,
        )

        summary = summarize_audit(
            results,
            threshold=args.threshold,
            lint_findings=lint_findings,
            fail_on_lint=args.fail_on_lint,
        )
        report_path = args.report or default_report_path(created_at)
        write_text_file(
            report_path,
            render_html_report(
                skill_path=args.file,
                provider=args.provider,
                model=args.model,
                summary=summary,
                results=results,
                created_at=created_at,
                redact=not args.no_redact,
            ),
        )

        progress.finish()
        print(f"Report written to {report_path}.")
        if not summary.passed:
            note = _build_failure_note(summary, fail_on_lint=args.fail_on_lint)
            print(f"FAILED ({summary.benchmark_score}%). Threshold: {args.threshold}%. {note}.")
            raise SystemExit(1)
        print(f"PASSED ({summary.benchmark_score}%). Threshold: {args.threshold}%.")
    except SystemExit:
        progress.finish()
        raise
    except Exception as error:
        progress.finish()
        hint = format_runtime_hint(
            args.provider,
            base_url=resolve_base_url(args.provider, args.url),
            error=error,
        )
        error_text = str(error)
        hint_text = hint
        if not args.no_redact:
            error_text = redact_text(error_text)
            hint_text = redact_text(hint_text)
        print(f"Run failed: {error_text}\n{hint_text}")
        raise SystemExit(2)
