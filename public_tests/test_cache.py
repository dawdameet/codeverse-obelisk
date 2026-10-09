import unittest

from support import StateTestCase, run, run_json

from obelisk.cache import LRUCache


class CacheUnit(unittest.TestCase):
    def test_hit_and_miss(self):
        c = LRUCache(2)
        self.assertIsNone(c.get("a"))
        c.put("a", 1)
        self.assertEqual(c.get("a"), 1)
        self.assertEqual((c.hits, c.misses), (1, 1))

    def test_capacity_and_eviction(self):
        c = LRUCache(2)
        for k in "abc":
            c.put(k, k)
        self.assertEqual(len(c), 2)
        self.assertIsNone(c.get("a"))
        self.assertEqual(c.evictions, 1)

    def test_reading_refreshes_recency(self):
        c = LRUCache(2)
        c.put("a", 1)
        c.put("b", 2)
        c.get("a")        # a is now the most recently used
        c.put("c", 3)     # so b is the one to go
        self.assertEqual(c.get("a"), 1)
        self.assertIsNone(c.get("b"))
        self.assertEqual(c.get("c"), 3)

    def test_overwrite_refreshes_recency(self):
        c = LRUCache(2)
        c.put("a", 1)
        c.put("b", 2)
        c.put("a", 10)
        c.put("c", 3)
        self.assertEqual(c.get("a"), 10)
        self.assertIsNone(c.get("b"))

    def test_keys_are_ordered_most_recent_first(self):
        c = LRUCache(3)
        for k in "abc":
            c.put(k, k)
        c.get("a")
        self.assertEqual(c.keys(), ["a", "c", "b"])

    def test_repeated_access_pattern(self):
        c = LRUCache(3)
        for k in "abc":
            c.put(k, k)
        for _ in range(3):
            c.get("a")
            c.get("b")
        c.put("d", "d")   # c was least recently used
        self.assertEqual(sorted(c.keys()), ["a", "b", "d"])

    def test_round_trip(self):
        c = LRUCache(3)
        for k in "abc":
            c.put(k, k)
        c.get("a")
        again = LRUCache.from_dict(c.to_dict(), 3)
        self.assertEqual(again.keys(), c.keys())

    def test_invalid_capacity(self):
        with self.assertRaises(ValueError):
            LRUCache(0)


class CacheCli(StateTestCase):
    cache_size = 3

    def search(self, q):
        return run_json("search", q, "--no-history")

    def test_miss_then_hit(self):
        self.assertEqual(self.search("vault")["cache"], "miss")
        self.assertEqual(self.search("vault")["cache"], "hit")

    def test_equivalent_queries_share_an_entry(self):
        self.search("vault AND security")
        self.assertEqual(self.search("  vault   AND  security ")["cache"], "hit")

    def test_no_cache_flag(self):
        self.assertEqual(run_json("search", "vault", "--no-cache")["cache"], "bypassed")
        self.assertEqual(run_json("cache")["size"], 0)

    def test_stats(self):
        self.search("vault")
        self.search("vault")
        stats = run_json("cache", "stats")
        self.assertEqual((stats["hits"], stats["misses"], stats["size"]), (1, 1, 1))
        self.assertEqual(stats["capacity"], 3)

    def test_eviction_through_the_cli(self):
        for q in ("vault", "treasury", "audit", "press"):
            self.search(q)
        stats = run_json("cache")
        self.assertEqual(stats["size"], 3)
        self.assertEqual(stats["evictions"], 1)
        self.assertEqual(self.search("vault")["cache"], "miss")

    def test_recently_used_entry_survives_eviction(self):
        for q in ("vault", "treasury", "audit"):
            self.search(q)
        self.assertEqual(self.search("vault")["cache"], "hit")   # refresh vault
        self.search("press")                                      # evicts treasury
        self.assertEqual(self.search("vault")["cache"], "hit")
        self.assertEqual(self.search("audit")["cache"], "hit")

    def test_clear(self):
        self.search("vault")
        run("cache", "clear")
        self.assertEqual(run_json("cache")["size"], 0)

    def test_cached_results_equal_fresh_results(self):
        first = self.search("security")
        second = self.search("security")
        self.assertEqual(first["results"], second["results"])


if __name__ == "__main__":
    unittest.main()
