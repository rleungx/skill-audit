from __future__ import annotations

import json
import pkgutil
import sys
from datetime import datetime
from importlib import resources
from pathlib import Path

from .evaluator import AuditSummary, CaseResult, RubricItem


_REPORT_APP_ID = "skill-audit-report-app"
_REPORT_DATA_ID = "skill-audit-report-data"


def _safe_json_for_html(data: object) -> str:
    # Prevent </script> breakouts by escaping '<' (and keep JSON valid).
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")


def _load_report_renderer_ts() -> str:
    data = pkgutil.get_data("skill_audit", "assets/report.ts")
    if isinstance(data, bytes):
        return data.decode("utf-8")

    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if isinstance(meipass, str) and meipass:
        candidates.append(Path(meipass) / "skill_audit" / "assets" / "report.ts")
    candidates.append(Path(__file__).resolve().parent / "assets" / "report.ts")

    for candidate in candidates:
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")

    try:
        return (
            resources.files("skill_audit")
            .joinpath("assets")
            .joinpath("report.ts")
            .read_text(encoding="utf-8")
        )
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Cannot load report renderer asset: {e}") from e


def _build_report_data(
    *,
    skill_path: str,
    provider: str,
    model: str,
    summary: AuditSummary,
    rubric: list[RubricItem],
    results: list[CaseResult],
    created_at: datetime,
) -> dict[str, object]:
    created = created_at.strftime("%Y-%m-%d %H:%M:%S")
    benchmark_score = max(0.0, min(100.0, float(summary.benchmark_score)))

    return {
        "createdAt": created,
        "skillPath": skill_path,
        "provider": provider,
        "model": model,
        "summary": {
            "mode": summary.mode,
            "referenceReady": bool(summary.reference_ready),
            "benchmarkScore": benchmark_score,
            "passThreshold": int(summary.pass_threshold),
            "passed": bool(summary.passed),
            "caseCount": int(summary.case_count),
            "scoredCaseCount": int(summary.scored_case_count),
            "violationCount": int(summary.violation_count),
            "hardFailRules": int(summary.hard_fail_rules),
            "blockingFailureCount": int(summary.blocking_failure_count),
            "criticalCasePassRate": summary.critical_case_pass_rate,
            "rulePassRate": summary.rule_pass_rate,
            "notApplicableRate": summary.not_applicable_rate,
        },
        "rubric": [
            {
                "rule": item.rule,
                "level": item.level,
                "why": item.why,
            }
            for item in rubric
        ],
        "results": [
            {
                "scenario": result.case.scenario,
                "userInput": result.case.user_input,
                "impact": result.case.impact,
                "aiResponse": result.ai_response,
                "benchmarkScore": result.judge.benchmark_score,
                "violation": bool(result.judge.violation),
                "blockingFailure": bool(result.judge.blocking_failure),
                "applicableRules": int(result.judge.applicable_rules),
                "passedRules": int(result.judge.passed_rules),
                "failedRules": int(result.judge.failed_rules),
                "notApplicableRules": int(result.judge.not_applicable_rules),
                "hardFailRules": int(result.judge.hard_fail_rules),
                "reason": result.judge.reason,
                "fixSuggestion": result.judge.fix_suggestion,
                "checklist": [
                    {
                        "rule": item.rule,
                        "level": item.level,
                        "status": item.status,
                        "notes": item.notes,
                    }
                    for item in result.judge.checklist
                ],
            }
            for result in results
        ],
    }


def render_html_report(
    *,
    skill_path: str,
    provider: str,
    model: str,
    summary: AuditSummary,
    rubric: list[RubricItem],
    results: list[CaseResult],
    created_at: datetime,
) -> str:
    renderer_ts = _load_report_renderer_ts()
    data_json = _safe_json_for_html(
        _build_report_data(
            skill_path=skill_path,
            provider=provider,
            model=model,
            summary=summary,
            rubric=rubric,
            results=results,
            created_at=created_at,
        )
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>skill-audit Report</title>
</head>
<body>
  <div id="{_REPORT_APP_ID}"></div>
  <script id="{_REPORT_DATA_ID}" type="application/json">{data_json}</script>
  <script>
{renderer_ts}
  </script>
</body>
</html>
"""
