"""Inverted index construction.

Documents are indexed in fixed-size segments so that very large datasets can
be processed (and later parallelised) in bounded chunks.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .models import Document
from .tokenizer import index_terms

SEGMENT_SIZE = 32


@dataclass
class InvertedIndex:
    postings: dict[str, dict[str, int]] = field(default_factory=dict)
    doc_ids: list[str] = field(default_factory=list)

    def add(self, doc: Document) -> None:
        tags = doc.metadata.get("tags", "")
        counts = Counter(index_terms(f"{doc.title} {tags} {doc.text}"))
        for term, tf in counts.items():
            self.postings.setdefault(term, {})[doc.id] = tf
        self.doc_ids.append(doc.id)

    def vocabulary(self) -> list[tuple[str, int]]:
        """(term, total occurrences) sorted by term."""
        return sorted(
            (term, sum(docs.values())) for term, docs in self.postings.items()
        )

    def to_dict(self) -> dict:
        return {"postings": self.postings, "doc_ids": self.doc_ids}

    @classmethod
    def from_dict(cls, raw: dict) -> "InvertedIndex":
        return cls(postings=raw["postings"], doc_ids=list(raw["doc_ids"]))


def build_index(documents: list[Document]) -> InvertedIndex:
    """Index every document, one segment at a time, in document-ID order."""
    docs = sorted(documents, key=lambda d: d.id)
    index = InvertedIndex()
    last = len(docs) - 1
    lo = 0
    while lo <= last:
        hi = min(lo + SEGMENT_SIZE - 1, last)  # inclusive end of this segment
        for i in range(lo, hi):
            index.add(docs[i])
        lo = hi + 1
    return index
