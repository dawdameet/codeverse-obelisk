import tempfile
import unittest
from pathlib import Path

from support import DATA, StateTestCase, run, run_json


class Ingestion(StateTestCase):
    ingest = False

    def test_commands_need_an_index(self):
        for argv in (("search", "vault"), ("inspect", "DOC-0001"),
                     ("suggest", "sec"), ("transaction", "TX-10005")):
            code, _, err = run(*argv)
            self.assertEqual(code, 6, argv)
            self.assertIn("ingest", err)

    def test_ingest_sample_data(self):
        result = run_json("ingest", str(DATA))
        self.assertEqual(result["documents"], 120)
        self.assertEqual(result["transactions"], 500)
        self.assertEqual(result["errors"], [])

    def test_ingest_default_path_uses_bundled_data(self):
        result = run_json("ingest")
        self.assertEqual(result["documents"], 120)

    def test_ingest_missing_path(self):
        code, _, err = run("ingest", str(DATA / "nope"))
        self.assertEqual(code, 3)
        self.assertIn("does not exist", err)

    def test_ingest_reports_malformed_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp, "good.txt")
            good.write_text("ID: DOC-9001\nTitle: Fine\nType: test\n---\nhello vault\n", encoding="utf-8")
            Path(tmp, "bad.txt").write_text("no header here", encoding="utf-8")
            result = run_json("ingest", tmp)
        self.assertEqual(result["documents"], 1)
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("bad.txt", result["errors"][0])

    def test_ingest_is_recursive(self):
        with tempfile.TemporaryDirectory() as tmp:
            nested = Path(tmp, "a", "b")
            nested.mkdir(parents=True)
            (nested / "deep.txt").write_text(
                "ID: DOC-9002\nTitle: Deep\nType: test\n---\ndeep vault\n", encoding="utf-8")
            result = run_json("ingest", tmp)
        self.assertEqual(result["documents"], 1)


class Inspection(StateTestCase):
    def test_inspect_document(self):
        code, out, _ = run("inspect", "DOC-0001")
        self.assertEqual(code, 0)
        for label in ("ID:", "Title:", "Type:", "Source:", "Preview:"):
            self.assertIn(label, out)
        self.assertIn("DOC-0001", out)

    def test_inspect_is_case_insensitive(self):
        self.assertEqual(run("inspect", "doc-0001")[0], 0)

    def test_inspect_json(self):
        doc = run_json("inspect", "DOC-0120")
        self.assertEqual(doc["id"], "DOC-0120")
        self.assertIn("text", doc)

    def test_inspect_missing_document(self):
        code, _, err = run("inspect", "DOC-9999")
        self.assertEqual(code, 3)
        self.assertIn("not found", err)
        self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main()
