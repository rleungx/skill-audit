from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from skill_audit.evaluator import AttackCase
from skill_audit.storage import default_report_path, default_snapshot_path, load_snapshot_cases, write_snapshot, write_text_file


class StorageTests(unittest.TestCase):
    def test_default_paths_use_consistent_timestamp_format(self) -> None:
        created_at = datetime(2026, 3, 6, 9, 8, 7, 123456)

        self.assertTrue(default_snapshot_path(created_at).endswith("snapshot_20260306_090807_123456.json"))
        self.assertTrue(default_report_path(created_at).endswith("report_20260306_090807_123456.html"))

    def test_write_snapshot_and_load_snapshot_cases_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "snapshot.json"
            write_snapshot(
                str(path),
                {
                    "version": 1,
                    "cases": [
                        {"scenario": "a", "input": "hello", "impact": "high"},
                        {"scenario": "b", "user_input": "hello", "severity": "critical"},
                    ],
                },
            )

            raw = json.loads(path.read_text(encoding="utf-8"))
            loaded = load_snapshot_cases(str(path))

        self.assertEqual(raw["version"], 1)
        self.assertEqual(loaded, [AttackCase(scenario="a", user_input="hello", impact="high")])

    def test_write_text_file_creates_parent_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "a" / "b" / "report.html"
            write_text_file(str(path), "hello")

            self.assertEqual(path.read_text(encoding="utf-8"), "hello")


if __name__ == "__main__":
    unittest.main()
