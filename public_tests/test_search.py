import unittest

from support import DATA, StateTestCase, indexed_ids, run, run_json

from obelisk.ingest import ingest_path
from obelisk.tokenizer import index_terms


def oracle():
    """Brute-force term sets for the indexed documents, from the source files."""
    result = ingest_path(DATA)
    indexed = indexed_ids()
    return {
        d.id: set(index_terms(f"{d.title} {d.metadata.get('tags', '')} {d.text}"))
        for d in result.documents
        if d.id in indexed
    }


class BasicSearch(StateTestCase):
    def test_single_term(self):
        expected = {d for d, terms in oracle().items() if "vault" in terms}
        result = run_json("search", "vault", "--limit", "500")
        self.assertEqual({r["id"] for r in result["results"]}, expected)
        self.assertEqual(result["total"], len(expected))

    def test_result_fields(self):
        result = run_json("search", "treasury", "--limit", "1")
        row = result["results"][0]
        for field in ("id", "title", "type", "score", "snippet"):
            self.assertIn(field, row)

    def test_human_output(self):
        code, out, _ = run("search", "vault")
        self.assertEqual(code, 0)
        self.assertIn("SEARCH: vault", out)
        self.assertIn("Cache:", out)

    def test_implicit_and(self):
        terms = oracle()
        expected = {d for d, t in terms.items() if {"royal", "mint"} <= t}
        result = run_json("search", "royal mint", "--limit", "500")
        self.assertEqual({r["id"] for r in result["results"]}, expected)

    def test_unknown_term_has_no_results(self):
        result = run_json("search", "zzzzqqqq")
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["results"], [])

    def test_ordering_is_deterministic_and_ranked(self):
        first = run_json("search", "security", "--limit", "50", "--no-cache")
        second = run_json("search", "security", "--limit", "50", "--no-cache")
        self.assertEqual(first["results"], second["results"])
        scores = [r["score"] for r in first["results"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        for a, b in zip(first["results"], first["results"][1:]):
            if a["score"] == b["score"]:
                self.assertLess(a["id"], b["id"])

    def test_limit(self):
        self.assertEqual(len(run_json("search", "vault", "--limit", "3")["results"]), 3)

    def test_invalid_limit(self):
        self.assertEqual(run("search", "vault", "--limit", "0")[0], 4)

    def test_hyphenated_compound_terms(self):
        expected = {d for d, t in oracle().items() if "security-log" in t}
        result = run_json("search", "security-log", "--limit", "500")
        self.assertEqual({r["id"] for r in result["results"]}, expected)

    def test_invalid_query(self):
        for bad in ("", "vault AND", "(vault", "vault)", "AND vault", "vault @"):
            code, _, err = run("search", bad)
            self.assertEqual(code, 4, repr(bad))
            self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main()
