import argparse
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from skill_audit.cli import main
from skill_audit.evaluator import AttackCase, AttackTurn, AuditSummary, RubricItem


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False)
        self.tmp_file.write(b"skill content")
        self.tmp_file.close()

    def tearDown(self):
        Path(self.tmp_file.name).unlink()

    def test_main_rejects_freeze_and_snapshot_together(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                main(["--file", self.tmp_file.name, "--model", "m", "--freeze", "--snapshot", "s.json"])
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("skill-audit --help", stdout.getvalue())

    def test_main_rejects_non_positive_concurrency(self) -> None:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                main(["--file", self.tmp_file.name, "--model", "m", "--concurrency", "0"])
        self.assertEqual(cm.exception.code, 2)

    def test_main_rejects_out_of_range_threshold(self) -> None:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                main(["--file", self.tmp_file.name, "--model", "m", "--threshold", "101"])
        self.assertEqual(cm.exception.code, 2)

    @patch("skill_audit.cli.build_client")
    @patch("skill_audit.cli.generate_frozen_attack_cases")
    @patch("skill_audit.cli.extract_judge_rubric")
    @patch("skill_audit.cli.write_snapshot")
    def test_main_freeze_mode_writes_snapshot_and_exits(self, mock_write, mock_rubric, mock_gen, mock_build) -> None:
        mock_gen.return_value = [AttackCase(scenario="case", turns=[AttackTurn("hello")], risk_category="r")]
        mock_rubric.return_value = [RubricItem("rule")]

        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            main(["--file", self.tmp_file.name, "--model", "m", "--freeze", "snap.json"])
        self.assertTrue(mock_write.called)
        self.assertIn("Snapshot saved to snap.json.", stdout.getvalue())

    @patch("skill_audit.cli.build_client")
    @patch("skill_audit.cli.generate_frozen_attack_cases")
    @patch("skill_audit.cli.extract_judge_rubric", return_value=[])
    @patch("skill_audit.cli.write_snapshot")
    def test_main_freeze_mode_rejects_empty_rubric(
        self,
        mock_write,
        mock_rubric,
        mock_gen,
        mock_build,
    ) -> None:
        mock_gen.return_value = [AttackCase(scenario="case", turns=[AttackTurn("hello")], risk_category="r")]

        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                main(["--file", self.tmp_file.name, "--model", "m", "--freeze", "snap.json"])

        self.assertEqual(cm.exception.code, 2)
        self.assertIn("No rubric rules were generated.", stdout.getvalue())
        self.assertFalse(mock_write.called)

    @patch("skill_audit.cli.write_text_file")
    @patch("skill_audit.cli.render_html_report", return_value="<html></html>")
    @patch("skill_audit.cli.summarize_audit")
    @patch("skill_audit.cli._run_case_evaluations", return_value=[])
    @patch(
        "skill_audit.cli._load_cases_and_rubric",
        return_value=([AttackCase("case", [AttackTurn("hello")], "r")], [RubricItem("rule")]),
    )
    @patch("skill_audit.cli._build_clients")
    def test_main_prints_report_path_and_threshold_on_success(
        self,
        mock_build_clients,
        mock_load_cases,
        mock_run_cases,
        mock_summary,
        mock_render_report,
        mock_write_text,
    ) -> None:
        mock_build_clients.return_value = (object(), object(), object())
        mock_summary.return_value = AuditSummary(True, 91.0, 0, 0, 0, [])

        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            main(["--file", self.tmp_file.name, "--model", "m", "--report", "out.html"])

        output = stdout.getvalue()
        self.assertIn("Report written to out.html.", output)
        self.assertIn("PASSED (91.0%). Threshold: 80%.", output)
        self.assertTrue(mock_write_text.called)
        self.assertTrue(mock_render_report.called)
        self.assertTrue(mock_load_cases.called)
        self.assertTrue(mock_run_cases.called)
        self.assertTrue(mock_build_clients.called)

    @patch("skill_audit.cli._load_cases_and_rubric", return_value=([], [RubricItem("rule")]))
    @patch("skill_audit.cli._build_clients")
    def test_main_rejects_zero_loaded_cases(self, mock_build_clients, mock_load_cases) -> None:
        mock_build_clients.return_value = (object(), object(), object())

        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                main(["--file", self.tmp_file.name, "--model", "m"])

        self.assertEqual(cm.exception.code, 2)
        self.assertIn("No audit cases were loaded.", stdout.getvalue())
        self.assertTrue(mock_load_cases.called)

    @patch("skill_audit.cli._load_cases_and_rubric", return_value=([AttackCase("case", [AttackTurn("hello")], "r")], []))
    @patch("skill_audit.cli._build_clients")
    def test_main_rejects_zero_loaded_rubric_rules(self, mock_build_clients, mock_load_cases) -> None:
        mock_build_clients.return_value = (object(), object(), object())

        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                main(["--file", self.tmp_file.name, "--model", "m"])

        self.assertEqual(cm.exception.code, 2)
        self.assertIn("No rubric rules were loaded.", stdout.getvalue())
        self.assertTrue(mock_load_cases.called)

    @patch("skill_audit.cli.load_snapshot")
    @patch("skill_audit.cli.build_client")
    def test_main_snapshot_mode_loads_and_runs(self, mock_build, mock_load) -> None:
        mock_load.return_value = {
            "cases": [AttackCase("s", [AttackTurn("i")], "r")],
            "rubric": [RubricItem("rule")],
            "metadata": {}
        }
        with patch("skill_audit.cli._evaluate_case") as mock_eval:
            mock_eval.side_effect = Exception("Stop execution")
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    main(["--file", self.tmp_file.name, "--model", "m", "--snapshot", "snap.json"])
        self.assertTrue(mock_load.called)

    @patch("skill_audit.cli.load_cache", return_value=None)
    @patch("skill_audit.cli.save_cache")
    @patch("skill_audit.cli.extract_judge_rubric", return_value=[RubricItem("rule")])
    @patch("skill_audit.cli.generate_attack_cases", return_value=[])
    def test_load_cases_and_rubric_skips_cache_write_when_generated_cases_are_empty(
        self,
        mock_generate,
        mock_rubric,
        mock_save_cache,
        mock_load_cache,
    ) -> None:
        from skill_audit.cli import _load_cases_and_rubric
        from skill_audit.progress import ProgressReporter

        args = argparse.Namespace(snapshot=None, no_cache=False, model="m")

        cases, rubric = _load_cases_and_rubric(
            args=args,
            skill_md="skill",
            attacker_client=MagicMock(),
            attacker_model="atk",
            judge_client=MagicMock(),
            judge_model="judge",
            progress=ProgressReporter(),
        )

        self.assertEqual(cases, [])
        self.assertEqual(rubric, [RubricItem("rule")])
        self.assertTrue(mock_load_cache.called)
        self.assertTrue(mock_generate.called)
        self.assertTrue(mock_rubric.called)
        self.assertFalse(mock_save_cache.called)

if __name__ == "__main__":
    unittest.main()
