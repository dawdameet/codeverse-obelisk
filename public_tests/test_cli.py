import subprocess
import sys
import unittest

import support
from support import run


class CliBasics(unittest.TestCase):
    def test_launcher_starts_and_reports_version(self):
        proc = subprocess.run(
            [sys.executable, str(support.LAUNCHER), "--version"],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), "OBELISK v1.0.0")

    def test_module_entry_point(self):
        import os
        env = dict(os.environ, PYTHONPATH=str(support.SRC))
        proc = subprocess.run(
            [sys.executable, "-m", "obelisk", "--version"],
            capture_output=True, text=True, timeout=60, env=env,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("OBELISK v", proc.stdout)

    def test_help_lists_commands(self):
        code, out, _ = run("--help")
        self.assertEqual(code, 0)
        for command in ("ingest", "inspect", "search", "history", "suggest",
                        "transaction", "cache", "logs", "status", "rebuild"):
            self.assertIn(command, out)

    def test_command_help_has_example(self):
        for command in ("search", "ingest", "inspect", "index", "suggest"):
            code, out, _ = run(command, "--help")
            self.assertEqual(code, 0, command)
            self.assertIn("example", out, command)

    def test_unknown_command_is_usage_error(self):
        code, _, err = run("frobnicate")
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", err)

    def test_no_command_prints_help(self):
        code, out, _ = run()
        self.assertEqual(code, 2)
        self.assertIn("usage", out.lower())


if __name__ == "__main__":
    unittest.main()
