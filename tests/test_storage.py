import json
import tempfile
import unittest
from pathlib import Path

from skill_audit.models import AttackCase, AttackTurn, RubricItem
from skill_audit.storage import load_cache, load_snapshot, save_cache, write_snapshot


class StorageTests(unittest.TestCase):
    def test_snapshot_roundtrip(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            data = {
                "version": 4,
                "metadata": {},
                "rubric": [{"rule": "rule", "level": "required"}],
                "cases": [{"scenario": "scen", "risk_category": "risk", "impact": "medium", "turns": ["in"]}]
            }
            write_snapshot(tmp_path, data)
            
            loaded = load_snapshot(tmp_path)
            self.assertEqual(len(loaded["cases"]), 1)
            self.assertEqual(loaded["cases"][0].scenario, "scen")
            self.assertEqual(loaded["rubric"][0].rule, "rule")
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    def test_cache_logic_respects_models(self) -> None:
        skill = "test skill"
        cases = [AttackCase("s", [AttackTurn("i")], "r")]
        rubric = [RubricItem("rule")]
        
        # Save cache for model A
        save_cache(skill, "modelA", "atkA", "jdgA", rubric, cases)
        
        # Load cache for model A should work
        cached = load_cache(skill, "modelA", "atkA", "jdgA")
        self.assertIsNotNone(cached)
        
        # Load cache for model B should fail
        cached_b = load_cache(skill, "modelB", "atkA", "jdgA")
        self.assertIsNone(cached_b)

    def test_load_snapshot_rejects_unsupported_version(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with Path(tmp_path).open("w", encoding="utf-8") as file:
                json.dump({"version": 3, "metadata": {}, "rubric": [], "cases": []}, file)
            with self.assertRaises(ValueError):
                load_snapshot(tmp_path)
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    def test_load_snapshot_rejects_invalid_cases_shape(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with Path(tmp_path).open("w", encoding="utf-8") as file:
                json.dump({"version": 4, "metadata": {}, "rubric": [], "cases": {}}, file)
            with self.assertRaises(ValueError):
                load_snapshot(tmp_path)
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

if __name__ == "__main__":
    unittest.main()
