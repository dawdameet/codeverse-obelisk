"""Executing a parsed query against the index and shaping the results."""

from __future__ import annotations

from . import config
from .indexer import InvertedIndex
from .models import Document
from .query_parser import canonical, evaluate, parse, positive_terms


def cache_key(query: str, limit: int) -> str:
    return f"{canonical(parse(query))}|limit={limit}"


def _snippet(doc: Document, terms: list[str]) -> str:
    text = " ".join(doc.text.split())
    lowered = text.lower()
    best = -1
    for term in terms:
        at = lowered.find(term)
        if at != -1 and (best == -1 or at < best):
            best = at
    start = max(0, (best if best != -1 else 0) - 20)
    piece = text[start : start + config.SNIPPET_WIDTH]
    return ("..." if start else "") + piece + ("..." if start + config.SNIPPET_WIDTH < len(text) else "")


def run_search(
    query: str,
    index: InvertedIndex,
    documents: dict[str, Document],
    limit: int,
) -> dict:
    tree = parse(query)
    matched = evaluate(tree, index.postings, set(index.doc_ids))
    terms = positive_terms(tree)
    scored = []
    for doc_id in matched:
        score = sum(index.postings.get(t, {}).get(doc_id, 0) for t in terms)
        scored.append((-score, doc_id))
    scored.sort()  # score descending, then document ID: fully deterministic
    results = []
    for neg_score, doc_id in scored[:limit]:
        doc = documents[doc_id]
        results.append(
            {
                "id": doc.id,
                "title": doc.title,
                "type": doc.type,
                "score": -neg_score,
                "snippet": _snippet(doc, terms),
            }
        )
    return {"query": query, "total": len(scored), "results": results}
