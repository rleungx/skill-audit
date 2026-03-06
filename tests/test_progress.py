from __future__ import annotations

import io
import unittest

from skill_audit.progress import ProgressReporter


class ProgressReporterTests(unittest.TestCase):
    def test_render_writes_plain_lines_when_not_tty(self) -> None:
        stream = io.StringIO()
        reporter = ProgressReporter(stream=stream, is_tty=False)

        reporter.render(42, "Loading", current=2, total=5)
        reporter.render(100, "Done")

        self.assertEqual(
            stream.getvalue(),
            "Progress:  42% (2/5) Loading\nProgress: 100% Done\n",
        )

    def test_run_with_spinner_executes_function(self) -> None:
        stream = io.StringIO()
        reporter = ProgressReporter(stream=stream, is_tty=False)

        result = reporter.run_with_spinner(10, "Working", lambda: "ok")

        self.assertEqual(result, "ok")
        self.assertIn("Progress:  10% Working", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
