import unittest

from skill_audit import api


class ApiTests(unittest.TestCase):
    def test_api_exports_common_public_entry_points(self) -> None:
        self.assertTrue(callable(api.generate_attack_cases))
        self.assertTrue(callable(api.generate_frozen_attack_cases))
        self.assertTrue(callable(api.extract_judge_rubric))
        self.assertTrue(callable(api.run_skill_response))
        self.assertTrue(callable(api.judge_case))
        self.assertTrue(callable(api.summarize_audit))
        self.assertTrue(callable(api.build_case_snapshot))
        self.assertTrue(callable(api.deserialize_attack_cases))

    def test_api_exports_common_models(self) -> None:
        self.assertEqual(api.AttackCase.__name__, "AttackCase")
        self.assertEqual(api.AttackTurn.__name__, "AttackTurn")
        self.assertEqual(api.RubricItem.__name__, "RubricItem")
        self.assertEqual(api.JudgeResult.__name__, "JudgeResult")
        self.assertEqual(api.AuditSummary.__name__, "AuditSummary")


if __name__ == "__main__":
    unittest.main()
