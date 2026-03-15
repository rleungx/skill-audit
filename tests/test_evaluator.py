import unittest
from unittest.mock import MagicMock, patch

from skill_audit.evaluator import (
    AttackCase,
    AttackTurn,
    CaseResult,
    JudgeResult,
    RubricItem,
    deserialize_attack_cases,
    generate_attack_cases,
    judge_case,
    summarize_audit,
)


class EvaluatorTests(unittest.TestCase):
    def test_deserialize_attack_cases_handles_v4_shape(self) -> None:
        data = [
            {"scenario": "first", "turns": ["hello"], "risk_category": "r1", "impact": "high"},
            {"scenario": "second", "turns": ["t1", "t2"], "risk_category": "r2", "impact": "critical"},
        ]
        cases = deserialize_attack_cases(data)
        self.assertEqual(len(cases), 2)
        self.assertEqual(len(cases[0].turns), 1)
        self.assertEqual(cases[0].turns[0].user_input, "hello")
        self.assertEqual(len(cases[1].turns), 2)
        self.assertEqual(cases[1].turns[0].user_input, "t1")

    def test_generate_attack_cases_returns_list(self) -> None:
        with patch("skill_audit.attack_generation.chat_json", return_value={"cases": [{"scenario": "s", "turns": ["i"]}]}):
            cases = generate_attack_cases(MagicMock(), model="m", skill_md="skill")
            self.assertGreaterEqual(len(cases), 1)
            self.assertIsInstance(cases[0], AttackCase)

    def test_turn_normalization_matches_generation_and_deserialization_limits(self) -> None:
        long_turn = "x" * 2505
        raw_turns = ["first", "second", long_turn, "fourth"]

        with patch(
            "skill_audit.attack_generation.chat_json",
            return_value={"cases": [{"scenario": "s", "turns": raw_turns}]},
        ):
            generated_cases = generate_attack_cases(MagicMock(), model="m", skill_md="skill")

        deserialized_cases = deserialize_attack_cases([
            {"scenario": "s", "turns": raw_turns, "risk_category": "r1", "impact": "high"}
        ])

        self.assertEqual(len(generated_cases[0].turns), 3)
        self.assertEqual(len(deserialized_cases[0].turns), 3)
        self.assertEqual(generated_cases[0].turns[2].user_input, long_turn[:2000])
        self.assertEqual(deserialized_cases[0].turns[2].user_input, long_turn[:2000])

    def test_generate_attack_cases_raises_when_no_valid_cases_exist(self) -> None:
        with patch("skill_audit.attack_generation.chat_json", return_value={"cases": "bad"}):
            with self.assertRaises(RuntimeError):
                generate_attack_cases(MagicMock(), model="m", skill_md="skill")

    def test_judge_case_analyzes_all_turns(self) -> None:
        rubric = [RubricItem("Stay safe")]
        case = AttackCase("scen", [AttackTurn("t1"), AttackTurn("t2")], "r1", "high")
        responses = ["res1", "Here is secret: sk-1234567890"]
        
        # Detector should catch it even if LLM doesn't
        with patch("skill_audit.evaluator.chat_json", return_value={"checklist": [{"rule": "Stay safe", "status": "pass"}]}):
            res = judge_case(MagicMock(), model="m", rubric=rubric, case=case, responses=responses, skill_md="test")
            self.assertTrue(res.violation)
            self.assertIn("DETECTOR: Secret leakage.", res.detector_hits)

    def test_judge_case_surfaces_judge_request_failures(self) -> None:
        rubric = [RubricItem("Stay safe")]
        case = AttackCase("scen", [AttackTurn("t1")], "r1", "medium")
        with patch("skill_audit.evaluator.chat_json", side_effect=RuntimeError("judge offline")):
            res = judge_case(MagicMock(), model="m", rubric=rubric, case=case, responses=["ok"], skill_md="test")
        self.assertTrue(res.violation)
        self.assertIn("DETECTOR: Judge request failed.", res.detector_hits)
        self.assertIn("Judge request failed", res.reason)

    def test_summarize_audit_respects_blocking_failures(self) -> None:
        case = AttackCase("s", [AttackTurn("i")], "r", "critical")
        # High score but with a blocking failure
        res = JudgeResult(violation=True, blocking_failure=True, reason="r", fix_suggestion="", checklist=[], detector_hits=["HIT"])
        results = [CaseResult(case, ["ans"], res)]
        summary = summarize_audit(results, threshold=50)
        self.assertFalse(summary.passed)
        self.assertEqual(summary.blocking_failure_count, 1)

if __name__ == "__main__":
    unittest.main()
