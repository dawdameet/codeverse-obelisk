"""Command-line interface. Parsing and printing only; logic lives elsewhere."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import bench, config, store
from .autocomplete import Autocomplete
from .cache import LRUCache
from .errors import (
    EXIT_INVALID,
    EXIT_NOT_FOUND,
    EXIT_NO_STATE,
    EXIT_OK,
    EXIT_USAGE,
    ObeliskError,
)
from .history import QueryHistory
from .indexer import InvertedIndex, build_index
from .ingest import ingest_path
from .logs import analyse
from .search import cache_key, run_search
from .transactions import TransactionTable
from .version import __version__

EXAMPLES = """\
examples:
  obelisk ingest
  obelisk search "vault AND security"
  obelisk search "(vault OR treasury) AND security" --json
  obelisk suggest sec
  obelisk transaction TX-10482
"""


def _emit(args, payload: dict, text: str) -> None:
    if getattr(args, "json", False):
        print(json.dumps(payload, sort_keys=True, indent=2))
    else:
        print(text)


# --- state helpers --------------------------------------------------------------


def _load_index() -> InvertedIndex:
    return InvertedIndex.from_dict(store.read_json(store.INDEX_FILE))


def _load_history() -> QueryHistory:
    raw = store.read_json(store.HISTORY_FILE, required=False)
    return QueryHistory.from_dict(raw) if raw else QueryHistory()


def _load_cache() -> LRUCache:
    raw = store.read_json(store.CACHE_FILE, required=False) or {}
    return LRUCache.from_dict(raw, config.cache_capacity())


def _build_derived(documents) -> InvertedIndex:
    index = build_index(documents)
    store.write_json(store.INDEX_FILE, index.to_dict())
    store.write_json(store.VOCAB_FILE, [list(e) for e in index.vocabulary()])
    return index


# --- commands ---------------------------------------------------------------------


def cmd_ingest(args) -> int:
    root = Path(args.path) if args.path else config.data_dir()
    result = ingest_path(root.resolve())
    store.save_store(result.documents, result.transactions, str(root.resolve()))
    index = _build_derived(result.documents)
    store.remove(store.CACHE_FILE)
    payload = {
        "documents": len(result.documents),
        "transactions": len(result.transactions),
        "indexed": len(index.doc_ids),
        "errors": result.errors,
        "files": result.files,
    }
    lines = [
        "INGESTION COMPLETE",
        "",
        f"Files read: {result.files}",
        f"Documents processed: {len(result.documents)}",
        f"Records indexed: {len(index.doc_ids)}",
        f"Transactions loaded: {len(result.transactions)}",
        f"Errors: {len(result.errors)}",
    ]
    lines += [f"  - {e}" for e in result.errors]
    _emit(args, payload, "\n".join(lines))
    return EXIT_OK


def cmd_inspect(args) -> int:
    docs, _, _ = store.load_store()
    wanted = args.id.strip().upper()
    doc = next((d for d in docs if d.id == wanted), None)
    if doc is None:
        raise ObeliskError(f"document not found: {wanted}", EXIT_NOT_FOUND)
    preview = " ".join(doc.text.split())[:200]
    lines = [
        f"ID:       {doc.id}",
        f"Title:    {doc.title}",
        f"Type:     {doc.type}",
        f"Source:   {doc.source}",
        "Metadata:",
    ]
    lines += [f"  {k}: {v}" for k, v in sorted(doc.metadata.items())]
    lines += ["Preview:", f"  {preview}"]
    _emit(args, doc.to_dict(), "\n".join(lines))
    return EXIT_OK


def cmd_search(args) -> int:
    if args.limit < 1:
        raise ObeliskError("--limit must be at least 1", EXIT_INVALID)
    docs, _, _ = store.load_store()
    index = _load_index()
    by_id = {d.id: d for d in docs}
    key = cache_key(args.query, args.limit)  # also validates the query

    cache = None if args.no_cache else _load_cache()
    outcome = None
    status = "bypassed"
    if cache is not None:
        outcome = cache.get(key)
        status = "hit" if outcome is not None else "miss"
    if outcome is None:
        outcome = run_search(args.query, index, by_id, args.limit)
        if cache is not None:
            cache.put(key, outcome)
    if cache is not None:
        store.write_json(store.CACHE_FILE, cache.to_dict())

    if not args.no_history:
        history = _load_history()
        history.push(args.query)
        store.write_json(store.HISTORY_FILE, history.to_dict())

    payload = dict(outcome, query=args.query, cache=status)
    lines = [
        f"SEARCH: {args.query}",
        f"Matches: {outcome['total']} (showing {len(outcome['results'])})",
        "",
    ]
    for n, r in enumerate(outcome["results"], start=1):
        lines.append(f"{n:>3}. {r['id']}  {r['title']}  [{r['type']}]  score={r['score']}")
        lines.append(f"     {r['snippet']}")
    lines += ["", f"Cache: {status.upper()}"]
    _emit(args, payload, "\n".join(lines))
    return EXIT_OK


def cmd_history(args) -> int:
    history = _load_history()
    action = args.action
    if action == "list":
        payload = {"states": history.states, "cursor": history.cursor}
        if not history.states:
            text = "History is empty."
        else:
            text = "\n".join(
                f"{'>' if i == history.cursor else ' '} {i + 1:>3}  {q}"
                for i, q in enumerate(history.states)
            )
        _emit(args, payload, text)
        return EXIT_OK
    if action == "clear":
        history.clear()
        store.write_json(store.HISTORY_FILE, history.to_dict())
        _emit(args, {"cleared": True}, "History cleared.")
        return EXIT_OK

    changed, query = history.undo() if action == "undo" else history.redo()
    store.write_json(store.HISTORY_FILE, history.to_dict())
    if not changed:
        _emit(
            args,
            {"changed": False, "query": query},
            f"Nothing to {action}.",
        )
        return EXIT_OK
    payload = {"changed": True, "query": query, "cursor": history.cursor}
    text = f"Restored query: {query}" if query else "Restored: (empty history state)"
    _emit(args, payload, text)
    if args.run and query:
        args2 = argparse.Namespace(
            query=query, limit=config.DEFAULT_RESULT_LIMIT, json=args.json,
            no_cache=False, no_history=True,
        )
        print()
        return cmd_search(args2)
    return EXIT_OK


def cmd_suggest(args) -> int:
    prefix = args.prefix.strip().lower()
    if not prefix:
        raise ObeliskError("prefix must not be empty", EXIT_INVALID)
    if args.limit < 1:
        raise ObeliskError("--limit must be at least 1", EXIT_INVALID)
    vocab = [tuple(e) for e in store.read_json(store.VOCAB_FILE)]
    found = Autocomplete(vocab).suggest(prefix, args.limit)
    payload = {
        "prefix": prefix,
        "suggestions": [{"term": t, "frequency": f} for t, f in found],
    }
    text = "\n".join(t for t, _ in found) if found else "(no suggestions)"
    _emit(args, payload, text)
    return EXIT_OK


def cmd_transaction(args) -> int:
    _, txs, _ = store.load_store()
    tx = TransactionTable(txs).get(args.id)
    lines = [
        "TRANSACTION",
        "",
        f"ID: {tx.id}",
        f"STATUS: {tx.status}",
        f"AMOUNT: {tx.amount}",
        f"DATE: {tx.date}",
        f"OPERATOR: {tx.operator}",
    ]
    _emit(args, tx.to_dict(), "\n".join(lines))
    return EXIT_OK


def cmd_cache(args) -> int:
    cache = _load_cache()
    if args.action == "clear":
        store.remove(store.CACHE_FILE)
        _emit(args, {"cleared": True}, "Cache cleared.")
        return EXIT_OK
    total = cache.hits + cache.misses
    payload = {
        "capacity": cache.capacity,
        "size": len(cache),
        "hits": cache.hits,
        "misses": cache.misses,
        "evictions": cache.evictions,
        "hit_rate": round(cache.hits / total, 4) if total else 0.0,
        "keys": cache.keys(),
    }
    lines = [
        "CACHE STATS",
        "",
        f"Capacity: {payload['capacity']}",
        f"Size: {payload['size']}",
        f"Hits: {cache.hits}",
        f"Misses: {cache.misses}",
        f"Evictions: {cache.evictions}",
        "Entries (most recent first):",
    ]
    lines += [f"  {k}" for k in payload["keys"]] or ["  (empty)"]
    _emit(args, payload, "\n".join(lines))
    return EXIT_OK


def cmd_logs(args) -> int:
    path = Path(args.file) if args.file else config.default_log_file()
    stats = analyse(path)
    lines = [
        f"LOG ANALYSIS: {stats['file']}",
        "",
        f"Total records: {stats['total']}",
        f"Successful: {stats['successful']}",
        f"Failed: {stats['failed']}",
        f"Malformed lines: {stats['malformed']}",
        f"Average duration (ms): {stats['avg_ms']}",
    ]
    for title, field in (
        ("By level", "by_level"),
        ("By status", "by_status"),
        ("By component", "by_component"),
        ("By operation", "by_operation"),
        ("By user", "by_user"),
    ):
        lines += ["", f"{title}:"]
        lines += [f"  {k}: {v}" for k, v in stats[field].items()]
    _emit(args, stats, "\n".join(lines))
    return EXIT_OK


def cmd_status(args) -> int:
    has_store = store.read_json(store.STORE_FILE, required=False)
    has_index = store.read_json(store.INDEX_FILE, required=False)
    vocab = store.read_json(store.VOCAB_FILE, required=False) or []
    docs = len(has_store["documents"]) if has_store else 0
    txs = len(has_store["transactions"]) if has_store else 0
    cache = _load_cache()
    ready = bool(has_store and has_index)
    payload = {
        "index": "READY" if ready else "MISSING",
        "documents": docs,
        "transactions": txs,
        "vocabulary": len(vocab),
        "cache": "READY",
        "cache_size": len(cache),
        "cache_capacity": cache.capacity,
    }
    lines = [
        "OBELISK STATUS",
        "",
        f"Index: {payload['index']}",
        f"Documents: {docs}",
        f"Transactions: {txs}",
        f"Vocabulary: {len(vocab):,}",
        f"Cache: READY ({len(cache)}/{cache.capacity})",
    ]
    _emit(args, payload, "\n".join(lines))
    return EXIT_OK


def cmd_index(args) -> int:
    docs, _, _ = store.load_store()
    index = _build_derived(docs)
    store.remove(store.CACHE_FILE)
    payload = {"documents": len(docs), "indexed": len(index.doc_ids),
               "terms": len(index.postings)}
    text = (
        "INDEX BUILT\n\n"
        f"Documents: {len(docs)}\nIndexed: {len(index.doc_ids)}\n"
        f"Distinct terms: {len(index.postings)}"
    )
    _emit(args, payload, text)
    return EXIT_OK


def cmd_rebuild(args) -> int:
    docs, txs, source = store.load_store()
    store.save_store(docs, txs, source)
    index = _build_derived(docs)
    store.remove(store.CACHE_FILE)
    payload = {"documents": len(docs), "indexed": len(index.doc_ids),
               "vocabulary": len(index.postings)}
    _emit(args, payload, "REBUILD COMPLETE\n\n"
          f"Documents: {len(docs)}\nIndexed: {len(index.doc_ids)}\n"
          f"Vocabulary: {len(index.postings)}")
    return EXIT_OK


def cmd_bench(args) -> int:
    result = bench.run_autocomplete(args.vocab, args.queries, args.seed, args.limit)
    text = "\n".join(f"{k}: {v}" for k, v in result.items())
    _emit(args, result, "BENCHMARK\n\n" + text)
    return EXIT_OK


# --- parser -----------------------------------------------------------------------


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # clean, argparse-style usage error
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"obelisk: error: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="obelisk",
        description="OBELISK - Search & Intelligence Engine for the Royal Mint.",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"OBELISK v{__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>", parser_class=_Parser)

    def add(name, func, help_, example):
        p = sub.add_parser(
            name, help=help_, description=help_,
            epilog=f"example:\n  {example}",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        p.add_argument("--json", action="store_true", help="machine-readable output")
        p.set_defaults(func=func)
        return p

    p = add("ingest", cmd_ingest, "ingest documents and transactions from a directory",
            "obelisk ingest data")
    p.add_argument("path", nargs="?", help="directory or file (default: bundled data/)")

    p = add("inspect", cmd_inspect, "show a stored document", "obelisk inspect DOC-0001")
    p.add_argument("id", help="document ID, e.g. DOC-0001")

    p = add("search", cmd_search, "search the index (supports AND, OR, NOT, parentheses)",
            'obelisk search "(vault OR treasury) AND security"')
    p.add_argument("query", help="search expression")
    p.add_argument("--limit", type=int, default=config.DEFAULT_RESULT_LIMIT)
    p.add_argument("--no-cache", action="store_true", help="bypass the query cache")
    p.add_argument("--no-history", action="store_true", help="do not record in history")

    p = add("history", cmd_history, "list, undo, redo or clear query history",
            "obelisk history undo")
    p.add_argument("action", nargs="?", default="list",
                   choices=["list", "undo", "redo", "clear"])
    p.add_argument("--run", action="store_true", help="re-run the restored query")

    p = add("suggest", cmd_suggest, "autocomplete suggestions for a prefix", "obelisk suggest sec")
    p.add_argument("prefix")
    p.add_argument("--limit", type=int, default=config.DEFAULT_SUGGEST_LIMIT)

    p = add("transaction", cmd_transaction, "look up a transaction by ID",
            "obelisk transaction TX-10482")
    p.add_argument("id", help="transaction ID, e.g. TX-10482")

    p = add("cache", cmd_cache, "show cache statistics or clear the cache", "obelisk cache stats")
    p.add_argument("action", nargs="?", default="stats", choices=["stats", "clear"])

    p = add("logs", cmd_logs, "analyse an operational log file", "obelisk logs data/logs/ops.log")
    p.add_argument("file", nargs="?", help="log file (default: bundled ops.log)")

    add("status", cmd_status, "show system status", "obelisk status")
    add("index", cmd_index, "rebuild the search index from stored documents", "obelisk index")
    add("rebuild", cmd_rebuild, "rebuild all derived state (index, vocabulary, cache)",
        "obelisk rebuild")

    p = add("bench", cmd_bench, "run the deterministic autocomplete benchmark workload",
            "obelisk bench --vocab 100000 --queries 500 --json")
    p.add_argument("--vocab", type=int, default=bench.DEFAULT_VOCAB)
    p.add_argument("--queries", type=int, default=bench.DEFAULT_QUERIES)
    p.add_argument("--seed", type=int, default=bench.DEFAULT_SEED)
    p.add_argument("--limit", type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    if not getattr(args, "func", None):
        parser.print_help()
        return EXIT_USAGE
    try:
        return args.func(args)
    except ObeliskError as exc:
        print(f"obelisk: error: {exc.message}", file=sys.stderr)
        return exc.code
    except BrokenPipeError:
        return EXIT_OK
