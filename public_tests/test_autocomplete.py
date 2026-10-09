import unittest

from support import StateTestCase, run, run_json

from obelisk import bench
from obelisk.autocomplete import Autocomplete


class AutocompleteUnit(unittest.TestCase):
    ENTRIES = [("secure", 4), ("security", 9), ("security-log", 9), ("seal", 1),
               ("second", 2), ("vault", 7)]

    def test_prefix_matches_ranked(self):
        got = Autocomplete(self.ENTRIES).suggest("sec", 10)
        self.assertEqual(got, [("security", 9), ("security-log", 9), ("secure", 4), ("second", 2)])

    def test_limit(self):
        self.assertEqual(len(Autocomplete(self.ENTRIES).suggest("s", 2)), 2)

    def test_no_match_and_exact(self):
        engine = Autocomplete(self.ENTRIES)
        self.assertEqual(engine.suggest("zzz", 5), [])
        self.assertEqual(engine.suggest("vault", 5), [("vault", 7)])

    def test_case_insensitive_prefix(self):
        self.assertEqual(Autocomplete(self.ENTRIES).suggest("SEC", 1)[0][0], "security")

    def test_input_order_does_not_matter(self):
        a = Autocomplete(self.ENTRIES).suggest("se", 10)
        b = Autocomplete(list(reversed(self.ENTRIES))).suggest("se", 10)
        self.assertEqual(a, b)


class AutocompleteCli(StateTestCase):
    def test_suggestions(self):
        code, out, _ = run("suggest", "sec")
        self.assertEqual(code, 0)
        lines = out.split()
        self.assertEqual(lines[0], "security")
        self.assertTrue(all(w.startswith("sec") for w in lines))

    def test_json_and_limit(self):
        data = run_json("suggest", "s", "--limit", "3")
        self.assertEqual(len(data["suggestions"]), 3)

    def test_empty_prefix_is_invalid(self):
        self.assertEqual(run("suggest", "  ")[0], 4)

    def test_no_suggestions(self):
        code, out, _ = run("suggest", "qqqq")
        self.assertEqual(code, 0)
        self.assertIn("no suggestions", out)


class AutocompleteScale(unittest.TestCase):
    def test_workload_is_deterministic(self):
        a = bench.run_autocomplete(2000, 50, 7)
        b = bench.run_autocomplete(2000, 50, 7)
        self.assertEqual(a["checksum"], b["checksum"])

    def test_large_vocabulary_stays_fast(self):
        """A generous smoke check; the official benchmark is stricter."""
        result = bench.run_autocomplete(100_000, 500, 1337)
        self.assertLess(result["query_seconds"], 1.0,
                        f"500 queries took {result['query_seconds']}s on 100k terms")


if __name__ == "__main__":
    unittest.main()
