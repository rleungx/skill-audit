from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from .lint import LintFinding
from .models import AuditSummary, CaseResult
from .redact import redact_text

_REPORT_DATA_ID = "skill-audit-report-data"
_REPORT_STYLES = """
    body { font-family: -apple-system, system-ui, sans-serif; padding: 2rem; background: #f4f7f6; color: #2c3e50; line-height: 1.6; }
    .container { max-width: 1100px; margin: 0 auto; }
    .card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 2rem; }
    .guidance-card { background: #f8fbff; border: 1px solid #d7e8f7; }
    .guidance-title { margin-bottom: 0.5rem; font-weight: bold; }
    .guidance-lead { margin-bottom: 0.75rem; color: #355c7d; }
    .guidance-list { margin: 0; padding-left: 1.2rem; }
    .guidance-list li { margin-bottom: 0.4rem; }
    .guidance-list li:last-child { margin-bottom: 0; }
    h1 { margin-top: 0; font-size: 1.8rem; border-left: 6px solid #3498db; padding-left: 1rem; }
    .matrix-row { display: grid; grid-template-columns: 200px 1fr 120px; gap: 1.5rem; align-items: center; margin-bottom: 0.8rem; font-size: 0.9rem; }
    .matrix-bar-bg { background: #eee; height: 10px; border-radius: 5px; overflow: hidden; }
    .matrix-bar-fill { background: #3498db; height: 100%; border-radius: 5px; }
    .result-card { background: white; border-radius: 8px; margin-bottom: 1rem; overflow: hidden; border: 1px solid #eee; transition: 0.2s; }
    .result-header { padding: 1rem; cursor: pointer; display: flex; align-items: center; gap: 1rem; background: #fff; }
    .result-header:hover { background: #fcfcfc; }
    .result-details { display: none; padding: 1rem; border-top: 1px solid #f9f9f9; background: #fafafa; }
    .expanded .result-details { display: block; }
    .fail-border { border-left: 5px solid #e74c3c; }
    .pass-border { border-left: 5px solid #2ecc71; }
    .badge { padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.75rem; font-weight: bold; text-transform: uppercase; background: #95a5a6; color: white; }
    pre { background: #2c3e50; color: #ecf0f1; padding: 1rem; border-radius: 6px; font-size: 0.85rem; white-space: pre-wrap; }
    .detector { color: #c0392b; }
    .status-summary { font-size: 1.4rem; font-weight: bold; margin-bottom: 1rem; }
    .pass-text { color: #2ecc71; }
    .fail-text { color: #e74c3c; }
    .lint-row { display: grid; grid-template-columns: 90px 240px 1fr; gap: 1rem; padding: 0.4rem 0; border-bottom: 1px solid #f1f1f1; align-items: center; }
    .lint-sev { font-weight: bold; text-transform: uppercase; font-size: 0.75rem; padding: 0.15rem 0.4rem; border-radius: 4px; text-align: center; color: white; }
    .sev-critical { background: #8e0e00; }
    .sev-high { background: #c0392b; }
    .sev-medium { background: #e67e22; }
    .sev-low { background: #7f8c8d; }
    .lint-code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.85rem; }
    .lint-evidence pre { margin-top: 0.4rem; background: #f8f8f8; color: #2c3e50; }
"""

def _maybe_redact(text: str, *, redact: bool) -> str:
    return redact_text(text) if redact else text


def _safe_json_for_html(data: object) -> str:
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")


def _build_report_payload(
    *,
    skill_path: str,
    provider: str,
    model: str,
    summary: AuditSummary,
    results: list[CaseResult],
    created_at: datetime,
    redact: bool,
) -> dict[str, object]:
    summary_matrix = [
        {
            "dimension": dimension.name,
            "passed": dimension.passed,
            "total": dimension.total,
            "score": dimension.score,
        }
        for dimension in summary.matrix
    ]
    lint_payload = [_build_lint_payload(finding, redact=redact) for finding in summary.lint_findings]
    result_payload = [_build_result_payload(result, redact=redact) for result in results]
    return {
        "createdAt": created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "skillPath": skill_path,
        "provider": provider,
        "model": model,
        "summary": {
            "benchmarkScore": summary.benchmark_score,
            "passed": bool(summary.passed),
            "caseCount": int(summary.case_count),
            "violationCount": int(summary.violation_count),
            "blockingFailureCount": int(summary.blocking_failure_count),
            "lintFindingCount": int(len(summary.lint_findings)),
            "lintBlockingCount": int(summary.lint_blocking_count),
            "matrix": summary_matrix,
        },
        "lintFindings": lint_payload,
        "results": result_payload,
    }


def _build_lint_payload(finding: LintFinding, *, redact: bool) -> dict[str, str]:
    return {
        "code": finding.code,
        "severity": finding.severity,
        "message": finding.message,
        "evidence": _maybe_redact(finding.evidence or "", redact=redact),
    }


def _build_result_payload(result: CaseResult, *, redact: bool) -> dict[str, object]:
    user_input = "\n\n".join(
        f"Turn {index + 1}: {_maybe_redact(turn.user_input, redact=redact)}"
        for index, turn in enumerate(result.case.turns)
    )
    ai_response = "\n\n".join(
        f"Response {index + 1}: {_maybe_redact(response, redact=redact)}"
        for index, response in enumerate(result.ai_responses)
    )
    return {
        "riskCategory": result.case.risk_category,
        "scenario": _maybe_redact(result.case.scenario, redact=redact),
        "userInput": user_input,
        "aiResponse": ai_response,
        "violation": bool(result.judge.violation),
        "blockingFailure": bool(result.judge.blocking_failure),
        "reason": _maybe_redact(result.judge.reason, redact=redact),
        "detectorHits": result.judge.detector_hits,
        "trace": {
            "attemptedToolUse": result.judge.trace.attempted_tool_use,
            "dangerousIntent": result.judge.trace.dangerous_intent,
        },
    }


def _build_lint_html(findings: list[LintFinding], *, blocking_count: int, redact: bool) -> str:
    if not findings:
        return """
    <div class="card">
        <div style="margin-bottom: 0.75rem; font-weight: bold;">Skill Lint</div>
        <div>No lint findings.</div>
    </div>"""

    rows = []
    for finding in findings:
        rows.append(
            f"""
        <div class="lint-row">
            <span class="lint-sev sev-{html.escape(finding.severity)}">{html.escape(finding.severity)}</span>
            <span class="lint-code">{html.escape(finding.code)}</span>
            <span class="lint-msg">{html.escape(finding.message)}</span>
        </div>"""
        )
        if finding.evidence:
            rows.append(
                f'<div class="lint-evidence"><pre>{html.escape(_maybe_redact(finding.evidence, redact=redact))}</pre></div>'
            )

    title = f"Skill Lint ({len(findings)} findings"
    if blocking_count:
        title += f", {blocking_count} blocking"
    title += ")"
    return f"""
    <div class="card">
        <div style="margin-bottom: 0.75rem; font-weight: bold;">{html.escape(title)}</div>
        <div class="lint-table">{''.join(rows)}</div>
    </div>"""


def _build_status_html(summary: AuditSummary) -> str:
    status_class = "pass-text" if summary.passed else "fail-text"
    status_text = "PASSED" if summary.passed else "FAILED"
    lint_summary = f"Skill Lint: {len(summary.lint_findings)} findings ({summary.lint_blocking_count} blocking)"
    return f"""
    <div class="card">
        <div class="status-summary">Status: <span class="{status_class}">{status_text}</span></div>
        <div style="margin-bottom: 0.75rem; color: #555;">{lint_summary}</div>
        <div class="matrix-container">{_build_summary_matrix_html(summary)}</div>
    </div>"""


def _build_guidance_html(summary: AuditSummary) -> str:
    if summary.lint_blocking_count or summary.blocking_failure_count:
        lead_parts: list[str] = []
        if summary.lint_blocking_count:
            lead_parts.append(
                f"{summary.lint_blocking_count} blocking lint finding{'s' if summary.lint_blocking_count != 1 else ''}"
            )
        if summary.blocking_failure_count:
            lead_parts.append(
                f"{summary.blocking_failure_count} blocking case{'s' if summary.blocking_failure_count != 1 else ''}"
            )
        lead = f"Start with {' and '.join(lead_parts)}."
    else:
        lead = "Start with the overall status, then scan the fastest fixes before revisiting the full trace."

    if summary.lint_findings:
        lint_step = f"Review Skill Lint next for {len(summary.lint_findings)} document-level issue{'s' if len(summary.lint_findings) != 1 else ''}."
    else:
        lint_step = "Review Skill Lint next to confirm the skill document is clean."

    if summary.violation_count:
        findings_step = (
            f"Open the {summary.violation_count} failing case card{'s' if summary.violation_count != 1 else ''} and read Judge Reason to see what broke first."
        )
    else:
        findings_step = "Open a passing case card or two to confirm the model behavior still matches your intent."

    return f"""
    <div class="card guidance-card">
        <div class="guidance-title">What to look at first</div>
        <div class="guidance-lead">{lead}</div>
        <ul class="guidance-list">
            <li>{lint_step}</li>
            <li>{findings_step}</li>
            <li>Use the score bars above to spot weaker dimensions before rewriting the whole skill.</li>
        </ul>
    </div>"""


def _build_summary_matrix_html(summary: AuditSummary) -> str:
    return "".join(
        f"""
        <div class="matrix-row">
            <span>{html.escape(dimension.name)}</span>
            <span class="matrix-bar-bg"><div class="matrix-bar-fill" style="width: {dimension.score}%"></div></span>
            <span>{dimension.passed}/{dimension.total} ({dimension.score}%)</span>
        </div>"""
        for dimension in summary.matrix
    )


def _build_trace_text(result: CaseResult, *, redact: bool) -> str:
    trace_lines: list[str] = []
    for turn_index, turn in enumerate(result.case.turns):
        trace_lines.append(f"Turn {turn_index + 1} User: {html.escape(_maybe_redact(turn.user_input, redact=redact))}")
        if turn_index < len(result.ai_responses):
            trace_lines.append(
                f"Turn {turn_index + 1} AI: {html.escape(_maybe_redact(result.ai_responses[turn_index], redact=redact))}"
            )
    return "\n".join(trace_lines)


def _build_detector_hits_html(detector_hits: list[str]) -> str:
    if not detector_hits:
        return ""
    detector_items = "".join(f"<li>{html.escape(hit)}</li>" for hit in detector_hits)
    return f'<div class="detail-section detector"><strong>Detector Hits:</strong><ul>{detector_items}</ul></div>'


def _build_result_card_html(result: CaseResult, *, redact: bool) -> str:
    status_class = "fail-border" if result.judge.violation else "pass-border"
    status_icon = "❌" if result.judge.violation else "✅"
    scenario = html.escape(_maybe_redact(result.case.scenario, redact=redact))
    risk_category = html.escape(result.case.risk_category)
    trace_html = _build_trace_text(result, redact=redact)
    judge_reason = html.escape(_maybe_redact(result.judge.reason, redact=redact))
    detector_html = _build_detector_hits_html(result.judge.detector_hits)
    return f"""
        <div class="result-card {status_class}">
            <div class="result-header" onclick="this.parentElement.classList.toggle('expanded')">
                <span class="badge {risk_category}">{risk_category}</span>
                <span class="scenario-text">{scenario}</span>
                <span class="status-icon">{status_icon}</span>
            </div>
            <div class="result-details">
                <div class="detail-section"><strong>Full Trace:</strong><pre>{trace_html}</pre></div>
                <div class="detail-section"><strong>Judge Reason:</strong><p>{judge_reason}</p></div>
                {detector_html}
            </div>
        </div>"""


def _build_results_html(results: list[CaseResult], *, redact: bool) -> str:
    return "".join(_build_result_card_html(result, redact=redact) for result in results)


def _build_page_html(
    *,
    skill_path: str,
    summary: AuditSummary,
    lint_html: str,
    results_html: str,
    report_data_json: str,
) -> str:
    skill_name = html.escape(Path(skill_path).name)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>skill-audit Industrial Report</title>
  <style>
{_REPORT_STYLES}
  </style>
</head>
<body>
  <div class="container">
    <h1>Security Audit: {skill_name}</h1>
    {_build_status_html(summary)}
    {_build_guidance_html(summary)}
    {lint_html}
    <div class="card">
        <div style="margin-bottom: 1rem; font-weight: bold;">Audit Findings ({summary.case_count} cases)</div>
        {results_html}
    </div>
  </div>
  <script id="{_REPORT_DATA_ID}" type="application/json">{report_data_json}</script>
</body>
</html>
"""


def render_html_report(
    *,
    skill_path: str,
    provider: str,
    model: str,
    summary: AuditSummary,
    results: list[CaseResult],
    created_at: datetime,
    redact: bool = True,
) -> str:
    report_payload = _build_report_payload(
        skill_path=skill_path,
        provider=provider,
        model=model,
        summary=summary,
        results=results,
        created_at=created_at,
        redact=redact,
    )
    report_data_json = _safe_json_for_html(report_payload)
    results_html = _build_results_html(results, redact=redact)
    lint_html = _build_lint_html(summary.lint_findings, blocking_count=summary.lint_blocking_count, redact=redact)
    return _build_page_html(
        skill_path=skill_path,
        summary=summary,
        lint_html=lint_html,
        results_html=results_html,
        report_data_json=report_data_json,
    )
