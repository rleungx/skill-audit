from __future__ import annotations

import json
import re
import unittest
from unittest.mock import patch

from skill_audit.report import _safe_json_for_html, render_html_report
from tests.support import sample_case_result, sample_created_at, sample_rubric, sample_summary


class ReportTests(unittest.TestCase):
    def test_safe_json_escapes_script_breakouts(self) -> None:
        self.assertEqual(_safe_json_for_html({"x": "</script>"}), '{"x": "\\u003c/script>"}')

    def test_render_html_report_embeds_payload_and_renderer(self) -> None:
        with patch("skill_audit.report._load_report_renderer_ts", return_value="console.log('report');"):
            html = render_html_report(
                skill_path="SKILL.md",
                provider="ollama",
                model="gpt-oss",
                summary=sample_summary(),
                rubric=sample_rubric(),
                results=[sample_case_result()],
                created_at=sample_created_at(),
            )

        self.assertIn("<title>skill-audit Report</title>", html)
        self.assertIn("console.log('report');", html)
        match = re.search(r'<script id="skill-audit-report-data" type="application/json">(.*?)</script>', html, re.S)
        self.assertIsNotNone(match)
        payload = json.loads(match.group(1))
        self.assertEqual(payload["provider"], "ollama")
        self.assertEqual(payload["model"], "gpt-oss")
        self.assertEqual(payload["summary"]["benchmarkScore"], 72.5)
        self.assertEqual(payload["results"][0]["impact"], "high")


if __name__ == "__main__":
    unittest.main()
