import io
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout

from oci_compute_idle_recommender.cli import main

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestCli(unittest.TestCase):
    def test_missing_file_exits_1(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(["/nonexistent/fleet.json"]), 1)

    def test_invalid_json_exits_1(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main([os.path.join(ROOT, "pyproject.toml")]), 1)

    def test_idle_sample_exits_2(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main([os.path.join(ROOT, "samples", "idle-fleet.json")])
        self.assertEqual(code, 2)
        text = out.getvalue()
        self.assertIn("IDLE001", text)
        self.assertIn("IDLE002", text)
        self.assertIn("IDLE003", text)
        self.assertIn("summary:", text)
        self.assertNotIn("old-stopped", text)

    def test_busy_sample_exits_0(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main([os.path.join(ROOT, "samples", "busy-fleet.json")])
        self.assertEqual(code, 0)
        self.assertIn("0 high", out.getvalue())


if __name__ == "__main__":
    unittest.main()
