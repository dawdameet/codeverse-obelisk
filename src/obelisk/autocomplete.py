"""Prefix suggestions over the indexed vocabulary.

Ranking: higher term frequency first, ties broken alphabetically.
"""

from __future__ import annotations


class Autocomplete:
    def __init__(self, entries: list[tuple[str, int]]) -> None:
        self._entries = list(entries)

    def __len__(self) -> int:
        return len(self._entries)

    def suggest(self, prefix: str, limit: int) -> list[tuple[str, int]]:
        prefix = prefix.lower()
        matches = [(term, freq) for term, freq in self._entries if term.startswith(prefix)]
        matches.sort(key=lambda entry: (-entry[1], entry[0]))
        return matches[:limit]
