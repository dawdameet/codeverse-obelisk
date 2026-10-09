import unittest

from support import DATA, StateTestCase, indexed_ids, run_json

from obelisk.errors import QueryError
from obelisk.ingest import ingest_path
from obelisk.query_parser import canonical, evaluate, parse
from obelisk.tokenizer import index_terms


class ParserTree(unittest.TestCase):
    def test_simple_forms(self):
        self.assertEqual(canonical(parse("vault")), "vault")
        self.assertEqual(canonical(parse("vault AND security")), "(vault AND security)")
        self.assertEqual(canonical(parse("vault OR treasury")), "(vault OR treasury)")

    def test_terms_are_case_insensitive_operators_are_not(self):
        self.assertEqual(canonical(parse("Vault AND Security")), "(vault AND security)")
        self.assertEqual(canonical(parse("vault and security")),
                         "((vault AND and) AND security)")

    def test_implicit_and(self):
        self.assertEqual(canonical(parse("royal mint vault")),
                         "((royal AND mint) AND vault)")

    def test_parentheses_group(self):
        self.assertEqual(canonical(parse("(vault OR treasury) AND security")),
                         "((vault OR treasury) AND security)")

    def test_and_binds_tighter_than_or(self):
        self.assertEqual(canonical(parse("a OR b AND c")), "(a OR (b AND c))")
        self.assertEqual(canonical(parse("a AND b OR c")), "((a AND b) OR c)")

    def test_not_binds_tighter_than_and(self):
        self.assertEqual(canonical(parse("NOT a AND b")), "((NOT a) AND b)")
        self.assertEqual(canonical(parse("a AND NOT b")), "(a AND (NOT b))")
        self.assertEqual(canonical(parse("NOT a OR b")), "((NOT a) OR b)")

    def test_nested_groups(self):
        self.assertEqual(canonical(parse("a AND (b OR (c AND d))")),
                         "(a AND (b OR (c AND d)))")
        self.assertEqual(canonical(parse("NOT (a OR b) AND c")),
                         "((NOT (a OR b)) AND c)")

    def test_left_associativity(self):
        self.assertEqual(canonical(parse("a OR b OR c")), "((a OR b) OR c)")

    def test_errors(self):
        for bad in ("", "   ", "AND", "a AND", "a OR OR b", "(a", "a)", "()", "a $ b"):
            with self.assertRaises(QueryError, msg=repr(bad)):
                parse(bad)


class ParserSemantics(StateTestCase):
    """Compare engine results with set algebra computed from the raw data."""

    def setUp(self):
        super().setUp()
        self.terms = {
            d.id: set(index_terms(f"{d.title} {d.metadata.get('tags', '')} {d.text}"))
            for d in ingest_path(DATA).documents
            if d.id in indexed_ids()
        }
        self.universe = set(self.terms)

    def has(self, word):
        return {d for d, t in self.terms.items() if word in t}

    def ids(self, query):
        return {r["id"] for r in run_json("search", query, "--limit", "500",
                                          "--no-cache", "--no-history")["results"]}

    def test_and(self):
        self.assertEqual(self.ids("vault AND security"),
                         self.has("vault") & self.has("security"))

    def test_or(self):
        self.assertEqual(self.ids("vault OR treasury"),
                         self.has("vault") | self.has("treasury"))

    def test_grouped(self):
        self.assertEqual(self.ids("(vault OR treasury) AND security"),
                         (self.has("vault") | self.has("treasury")) & self.has("security"))

    def test_mixed_precedence(self):
        self.assertEqual(self.ids("vault OR treasury AND security"),
                         self.has("vault") | (self.has("treasury") & self.has("security")))

    def test_not_leading(self):
        self.assertEqual(self.ids("NOT vault AND security"),
                         (self.universe - self.has("vault")) & self.has("security"))

    def test_not_trailing(self):
        self.assertEqual(self.ids("security AND NOT vault"),
                         self.has("security") - self.has("vault"))

    def test_not_group(self):
        self.assertEqual(self.ids("NOT (vault OR treasury) AND audit"),
                         (self.universe - (self.has("vault") | self.has("treasury")))
                         & self.has("audit"))

    def test_deep_nesting(self):
        expected = self.has("royal") & (self.has("vault") | (self.has("mint") & self.has("audit")))
        self.assertEqual(self.ids("royal AND (vault OR (mint AND audit))"), expected)


if __name__ == "__main__":
    unittest.main()
