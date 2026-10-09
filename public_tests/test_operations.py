import unittest

from support import DATA, StateTestCase, run, run_json


class Logs(StateTestCase):
    ingest = False

    def test_log_statistics(self):
        stats = run_json("logs", str(DATA / "logs" / "ops.log"))
        self.assertEqual(stats["total"], 600)
        self.assertEqual(stats["successful"] + stats["failed"], 600)
        self.assertEqual(sum(stats["by_status"].values()), 600)
        self.assertEqual(sum(stats["by_level"].values()), 600)
        self.assertEqual(stats["successful"], stats["by_status"]["OK"])

    def test_default_file(self):
        self.assertEqual(run_json("logs")["total"], 600)

    def test_human_output(self):
        code, out, _ = run("logs")
        self.assertEqual(code, 0)
        for label in ("Total records", "Successful", "Failed", "By status"):
            self.assertIn(label, out)

    def test_deterministic(self):
        self.assertEqual(run("logs")[1], run("logs")[1])

    def test_missing_file(self):
        self.assertEqual(run("logs", str(DATA / "logs" / "missing.log"))[0], 3)

    def test_malformed_lines_are_counted(self):
        import tempfile, pathlib
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp, "x.log")
            p.write_text("garbage\n2025-01-01T00:00:00Z INFO c op=a status=OK user=u ms=5\n",
                         encoding="utf-8")
            stats = run_json("logs", str(p))
        self.assertEqual((stats["total"], stats["malformed"]), (1, 1))


class Status(StateTestCase):
    def test_status(self):
        code, out, _ = run("status")
        self.assertEqual(code, 0)
        for text in ("OBELISK STATUS", "Index: READY", "Documents: 120", "Transactions: 500"):
            self.assertIn(text, out)

    def test_status_without_state(self):
        self.tearDown(); self.ingest = False; self.setUp()
        self.assertIn("Index: MISSING", run("status")[1])


class Rebuild(StateTestCase):
    def test_rebuild_restores_state(self):
        before = run_json("search", "vault", "--no-history", "--limit", "500")["results"]
        code, out, _ = run("rebuild")
        self.assertEqual(code, 0)
        self.assertIn("REBUILD COMPLETE", out)
        after = run_json("search", "vault", "--no-history", "--limit", "500")["results"]
        self.assertEqual(before, after)

    def test_rebuild_clears_cache_but_not_history(self):
        run_json("search", "vault")
        run("rebuild")
        self.assertEqual(run_json("cache")["size"], 0)
        self.assertEqual(run_json("history")["states"], ["vault"])

    def test_rebuild_is_deterministic(self):
        run("rebuild")
        a = run_json("status")
        run("rebuild")
        self.assertEqual(a, run_json("status"))

    def test_source_data_untouched(self):
        before = sorted(p.stat().st_size for p in DATA.rglob("*") if p.is_file())
        run("rebuild")
        self.assertEqual(before, sorted(p.stat().st_size for p in DATA.rglob("*") if p.is_file()))

    def test_rebuild_without_state(self):
        self.tearDown(); self.ingest = False; self.setUp()
        self.assertEqual(run("rebuild")[0], 6)


class WorkingDirectory(StateTestCase):
    def test_independent_of_cwd(self):
        import os, tempfile
        old = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                self.assertEqual(run_json("ingest")["documents"], 120)
            finally:
                os.chdir(old)


if __name__ == "__main__":
    unittest.main()
