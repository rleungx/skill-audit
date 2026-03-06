from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from skill_audit.evaluator import AttackCase


class CliTests(unittest.TestCase):
    def test_main_rejects_freeze_and_snapshot_together(self) -> None:
        from skill_audit.cli import main

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as exc:
                main(
                    [
                        "--file",
                        "SKILL.md",
                        "--model",
                        "gpt-oss",
                        "--freeze",
                        "--snapshot",
                        "snapshot.json",
                    ]
                )

        self.assertEqual(exc.exception.code, 2)
        self.assertIn("use either --freeze or --snapshot", stderr.getvalue())

    def test_main_freeze_mode_writes_snapshot_and_exits_zero(self) -> None:
        from skill_audit.cli import main

        stdout = io.StringIO()
        cases = [AttackCase(scenario="case", user_input="hello", impact="high")]
        with (
            redirect_stdout(stdout),
            patch("skill_audit.cli.resolve_base_url", return_value="http://localhost"),
            patch("skill_audit.cli.resolve_api_key", return_value=""),
            patch("skill_audit.cli.build_client", return_value=object()),
            patch("pathlib.Path.read_text", return_value="# Skill"),
            patch("skill_audit.cli.generate_frozen_attack_cases", return_value=cases),
            patch("skill_audit.cli.default_snapshot_path", return_value="/tmp/frozen.json"),
            patch("skill_audit.cli.write_snapshot") as write_snapshot,
        ):
            with self.assertRaises(SystemExit) as exc:
                main(["--file", "SKILL.md", "--model", "gpt-oss", "--freeze"])

        self.assertEqual(exc.exception.code, 0)
        write_snapshot.assert_called_once()
        self.assertIn("Saved 1 cases to snapshot /tmp/frozen.json", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
