import unittest

from support import StateTestCase, run, run_json

from obelisk.history import QueryHistory


class HistoryUnit(unittest.TestCase):
    def test_push_and_current(self):
        h = QueryHistory()
        self.assertIsNone(h.current)
        h.push("a")
        h.push("b")
        self.assertEqual(h.current, "b")
        self.assertEqual(h.states, ["a", "b"])

    def test_undo_restores_previous(self):
        h = QueryHistory()
        for q in "abc":
            h.push(q)
        self.assertEqual(h.undo(), (True, "b"))
        self.assertEqual(h.undo(), (True, "a"))
        self.assertEqual(h.undo(), (True, None))
        self.assertEqual(h.undo(), (False, None))

    def test_redo_walks_forward(self):
        h = QueryHistory()
        for q in "abc":
            h.push(q)
        h.undo()
        h.undo()
        self.assertEqual(h.redo(), (True, "b"))
        self.assertEqual(h.redo(), (True, "c"))
        self.assertEqual(h.redo(), (False, "c"))

    def test_new_query_discards_undone_states(self):
        h = QueryHistory()
        for q in "abc":
            h.push(q)
        h.undo()          # current b
        h.push("d")       # c is gone
        self.assertEqual(h.states, ["a", "b", "d"])
        self.assertEqual(h.undo(), (True, "b"))
        self.assertEqual(h.undo(), (True, "a"))

    def test_repeated_undo_redo_cycles(self):
        h = QueryHistory()
        for q in "abcde":
            h.push(q)
        for expected in "dcb":
            self.assertEqual(h.undo()[1], expected)
        for expected in "cde":
            self.assertEqual(h.redo()[1], expected)

    def test_clear(self):
        h = QueryHistory()
        h.push("a")
        h.clear()
        self.assertEqual((h.states, h.current), ([], None))

    def test_round_trip(self):
        h = QueryHistory()
        for q in "abc":
            h.push(q)
        h.undo()
        again = QueryHistory.from_dict(h.to_dict())
        self.assertEqual((again.states, again.cursor), (h.states, h.cursor))


class HistoryCli(StateTestCase):
    def search(self, q):
        run_json("search", q)

    def test_searches_are_recorded(self):
        for q in ("vault", "treasury"):
            self.search(q)
        self.assertEqual(run_json("history")["states"], ["vault", "treasury"])

    def test_no_history_flag(self):
        run_json("search", "vault", "--no-history")
        self.assertEqual(run_json("history")["states"], [])

    def test_undo_then_redo(self):
        for q in ("vault", "treasury", "audit"):
            self.search(q)
        self.assertEqual(run_json("history", "undo")["query"], "treasury")
        self.assertEqual(run_json("history", "redo")["query"], "audit")

    def test_undo_after_new_search(self):
        for q in ("vault", "treasury", "audit"):
            self.search(q)
        run_json("history", "undo")      # back to treasury
        self.search("press")             # audit is discarded
        self.assertEqual(run_json("history", "undo")["query"], "treasury")
        self.assertEqual(run_json("history", "undo")["query"], "vault")

    def test_undo_with_empty_history(self):
        code, out, _ = run("history", "undo")
        self.assertEqual(code, 0)
        self.assertIn("Nothing to undo", out)

    def test_clear(self):
        self.search("vault")
        run("history", "clear")
        self.assertEqual(run_json("history")["states"], [])

    def test_undo_run_executes_restored_query(self):
        self.search("vault")
        self.search("treasury")
        code, out, _ = run("history", "undo", "--run")
        self.assertEqual(code, 0)
        self.assertIn("SEARCH: vault", out)


if __name__ == "__main__":
    unittest.main()
