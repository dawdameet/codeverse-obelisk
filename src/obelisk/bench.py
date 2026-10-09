"""Deterministic autocomplete workload for external benchmark runners.

The vocabulary and the queries are derived from a fixed-seed generator, so the
same arguments always produce the same workload and the same checksum.
"""

from __future__ import annotations

import hashlib
import time

from .autocomplete import Autocomplete

_SYLLABLES = (
    "ba be bi bo bu ca ce ci co cu da de di do du fa fe fi fo fu ga ge gi go gu "
    "ka ke ki ko ku la le li lo lu ma me mi mo mu na ne ni no nu pa pe pi po pu "
    "ra re ri ro ru sa se si so su ta te ti to tu va ve vi vo vu za ze zi zo zu"
).split()

DEFAULT_VOCAB = 100_000
DEFAULT_QUERIES = 500
DEFAULT_SEED = 1337


class _Lcg:
    def __init__(self, seed: int) -> None:
        self.state = seed % (2**32)

    def below(self, n: int) -> int:
        self.state = (1664525 * self.state + 1013904223) % (2**32)
        return (self.state >> 8) % n


def make_vocabulary(size: int, seed: int) -> list[tuple[str, int]]:
    rng = _Lcg(seed)
    seen: dict[str, int] = {}
    while len(seen) < size:
        word = "".join(
            _SYLLABLES[rng.below(len(_SYLLABLES))] for _ in range(2 + rng.below(3))
        )
        if word not in seen:
            seen[word] = 1 + rng.below(1000)
    return sorted(seen.items())


def make_queries(vocab: list[tuple[str, int]], count: int, seed: int) -> list[str]:
    rng = _Lcg(seed + 1)
    queries = []
    for _ in range(count):
        term = vocab[rng.below(len(vocab))][0]
        queries.append(term[: min(len(term), 3 + rng.below(3))])
    return queries


def run_autocomplete(
    vocab_size: int = DEFAULT_VOCAB,
    queries: int = DEFAULT_QUERIES,
    seed: int = DEFAULT_SEED,
    limit: int = 10,
) -> dict:
    vocab = make_vocabulary(vocab_size, seed)
    prefixes = make_queries(vocab, queries, seed)

    started = time.perf_counter()
    engine = Autocomplete(vocab)
    build_seconds = time.perf_counter() - started

    digest = hashlib.sha256()
    started = time.perf_counter()
    for prefix in prefixes:
        found = engine.suggest(prefix, limit)
        digest.update((prefix + ":" + ",".join(t for t, _ in found) + "\n").encode())
    query_seconds = time.perf_counter() - started

    return {
        "benchmark": "autocomplete",
        "vocabulary": vocab_size,
        "queries": queries,
        "seed": seed,
        "limit": limit,
        "checksum": digest.hexdigest(),
        "build_seconds": round(build_seconds, 4),
        "query_seconds": round(query_seconds, 4),
    }
