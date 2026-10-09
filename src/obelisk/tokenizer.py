"""Text tokenisation shared by the indexer and the query parser."""

from __future__ import annotations

import re

# A word is letters/digits, optionally joined by hyphens ("security-log").
_WORD = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def words(text: str) -> list[str]:
    """Lower-cased words in order of appearance, compounds kept whole."""
    return _WORD.findall(text.lower())


def index_terms(text: str) -> list[str]:
    """Terms contributed to the index: each compound plus its parts."""
    terms: list[str] = []
    for word in words(text):
        terms.append(word)
        if "-" in word:
            terms.extend(word.split("-"))
    return terms
