import unittest
from datetime import datetime

from skill_audit.lint import LintFinding
from skill_audit.models import AttackCase, AttackTurn, AuditSummary, CaseResult, JudgeResult, TraceInfo
from skill_audit.report import render_html_report


class ReportTests(unittest.TestCase):
    def test_render_html_report_runs_without_error(self) -> None:
        summary = AuditSummary(True, 100.0, 1, 0, 0, [])
        case = AttackCase("scenario <script>", [AttackTurn("input")], "risk")
        # Use real objects instead of Mocks to avoid serialization errors
        res = JudgeResult(
            violation=False, 
            blocking_failure=False, 
            reason="reason <script>", 
            fix_suggestion="", 
            checklist=[], 
            detector_hits=["hit <script>"],
            trace=TraceInfo(attempted_tool_use=True, dangerous_intent=False)
        )
        results = [CaseResult(case, ["ans <script>"], res)]
        
        html_out = render_html_report(
            skill_path="SKILL.md",
            provider="p",
            model="m",
            summary=summary,
            results=results,
            created_at=datetime.now()
        )
        self.assertIn("Security Audit", html_out)
        self.assertIn("What to look at first", html_out)
        # Check XSS escaping
        self.assertIn("&lt;script&gt;", html_out)
        self.assertNotIn("<script>", html_out.split("<script id=")[0])

    def test_render_html_report_places_guidance_after_status_and_before_lint(self) -> None:
        lint_findings = [LintFinding("RULE_1", "high", "Fix this")]
        summary = AuditSummary(False, 40.0, 2, 1, 1, [], lint_findings=lint_findings, lint_blocking_count=1)
        case = AttackCase("scenario", [AttackTurn("input")], "risk")
        res = JudgeResult(
            violation=True,
            blocking_failure=True,
            reason="reason",
            fix_suggestion="",
            checklist=[],
            detector_hits=[],
            trace=TraceInfo(attempted_tool_use=False, dangerous_intent=False),
        )
        html_out = render_html_report(
            skill_path="SKILL.md",
            provider="p",
            model="m",
            summary=summary,
            results=[CaseResult(case, ["answer"], res)],
            created_at=datetime.now(),
        )

        status_index = html_out.index("Status:")
        guidance_index = html_out.index("What to look at first")
        lint_index = html_out.index("Skill Lint (1 findings, 1 blocking)")

        self.assertLess(status_index, guidance_index)
        self.assertLess(guidance_index, lint_index)
        self.assertIn("Start with 1 blocking lint finding and 1 blocking case.", html_out)
        self.assertIn("Open the 1 failing case card and read Judge Reason to see what broke first.", html_out)

    def test_render_html_report_redacts_suspected_secrets_by_default(self) -> None:
        summary = AuditSummary(True, 100.0, 1, 0, 0, [])
        case = AttackCase("scenario", [AttackTurn("input")], "risk")
        res = JudgeResult(
            violation=True,
            blocking_failure=True,
            reason="reason",
            fix_suggestion="",
            checklist=[],
            detector_hits=["DETECTOR: Secret leakage."],
            trace=TraceInfo(attempted_tool_use=False, dangerous_intent=False),
        )
        results = [CaseResult(case, ["leak sk-1234567890"], res)]
        html_out = render_html_report(
            skill_path="SKILL.md",
            provider="p",
            model="m",
            summary=summary,
            results=results,
            created_at=datetime.now(),
        )
        self.assertNotIn("sk-1234567890", html_out)
        self.assertIn("sk-[REDACTED]", html_out)

if __name__ == "__main__":
    unittest.main()
