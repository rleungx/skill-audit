from __future__ import annotations

import unittest
from unittest.mock import patch

from skill_audit.evaluator import (
    AttackCase,
    CaseResult,
    ChecklistResult,
    JudgeResult,
    RubricItem,
    deserialize_attack_cases,
    extract_judge_rubric,
    generate_attack_cases,
    judge_case,
    summarize_audit,
)
from tests.support import sample_case_result


class EvaluatorTests(unittest.TestCase):
    def test_deserialize_attack_cases_dedupes_and_normalizes_impact(self) -> None:
        cases = deserialize_attack_cases(
            [
                {"scenario": "a", "input": "same", "impact": "crit"},
                {"scenario": "b", "user_input": "same", "severity": "high"},
                {"scenario": "c", "input": "other", "impact": "unknown"},
            ]
        )

        self.assertEqual(len(cases), 2)
        self.assertEqual(cases[0], AttackCase(scenario="a", user_input="same", impact="critical"))
        self.assertEqual(cases[1], AttackCase(scenario="c", user_input="other", impact="medium"))

    def test_extract_judge_rubric_normalizes_and_dedupes(self) -> None:
        with patch(
            "skill_audit.evaluator.chat_json",
            return_value={
                "rubric": [
                    {"rule": "Use approval", "level": "must", "why": "safety"},
                    {"rule": "use approval", "level": "required", "why": "duplicate"},
                    "Keep files checked",
                ]
            },
        ):
            rubric = extract_judge_rubric(object(), model="demo", skill_md="skill")

        self.assertEqual(
            rubric,
            [
                RubricItem(rule="Keep files checked", level="required", why=""),
                RubricItem(rule="Use approval", level="hard", why="safety"),
            ],
        )

    def test_generate_attack_cases_backfills_with_fallback_cases(self) -> None:
        with patch(
            "skill_audit.evaluator.chat_json",
            return_value={"cases": [{"scenario": "x", "input": "hello", "impact": "high"}]},
        ):
            cases = generate_attack_cases(object(), model="demo", skill_md="skill")

        self.assertGreaterEqual(len(cases), 5)
        self.assertEqual(cases[0], AttackCase(scenario="x", user_input="hello", impact="high"))

    def test_judge_case_retries_when_everything_is_not_applicable(self) -> None:
        rubric = [RubricItem(rule="Use approval", level="hard", why="safety")]
        with patch(
            "skill_audit.evaluator.chat_json",
            side_effect=[
                {
                    "reason": "unclear",
                    "fix_suggestion": "none",
                    "checklist": [{"rule": "Use approval", "status": "not_applicable", "notes": "na"}],
                },
                {
                    "reason": "failed hard rule",
                    "fix_suggestion": "ask first",
                    "checklist": [{"rule": "Use approval", "status": "fail", "notes": "missing"}],
                },
            ],
        ) as chat_json:
            result = judge_case(
                object(),
                model="demo",
                rubric=rubric,
                impact="critical",
                user_input="force-push now",
                ai_response="I will do it",
            )

        self.assertTrue(result.violation)
        self.assertTrue(result.blocking_failure)
        self.assertEqual(result.failed_rules, 1)
        self.assertEqual(chat_json.call_count, 2)

    def test_summarize_audit_computes_weighted_score(self) -> None:
        passing = CaseResult(
            case=AttackCase(scenario="safe", user_input="check", impact="critical"),
            ai_response="I refuse.",
            judge=JudgeResult(
                benchmark_score=100.0,
                violation=False,
                blocking_failure=False,
                applicable_rules=1,
                passed_rules=1,
                failed_rules=0,
                not_applicable_rules=0,
                hard_fail_rules=0,
                reason="good",
                fix_suggestion="",
                checklist=[ChecklistResult(rule="Use approval", level="hard", status="pass", notes="ok")],
            ),
        )
        failing = sample_case_result(impact="medium", score=50.0)

        summary = summarize_audit([passing, failing], mode="snapshot", threshold=80)

        self.assertEqual(summary.benchmark_score, 83.3)
        self.assertTrue(summary.reference_ready)
        self.assertEqual(summary.violation_count, 1)
        self.assertTrue(summary.passed)


if __name__ == "__main__":
    unittest.main()
