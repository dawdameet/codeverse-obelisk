"""On-disk state: documents, transactions, index, vocabulary, history, cache."""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import config
from .errors import EXIT_CORRUPT, EXIT_NO_STATE, ObeliskError
from .models import Document, Transaction

STORE_FILE = "store.json"
INDEX_FILE = "index.json"
VOCAB_FILE = "vocab.json"
HISTORY_FILE = "history.json"
CACHE_FILE = "cache.json"


def _path(name: str) -> Path:
    return config.state_dir() / name


def write_json(name: str, payload) -> None:
    target = _path(name)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, sort_keys=True, indent=1)
        handle.write("\n")
    os.replace(tmp, target)


def read_json(name: str, required: bool = True):
    target = _path(name)
    if not target.exists():
        if required:
            raise ObeliskError(
                "no index found - run `obelisk ingest` first", EXIT_NO_STATE
            )
        return None
    try:
        with open(target, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as exc:
        raise ObeliskError(f"state file {name} is corrupt: {exc}", EXIT_CORRUPT)


def remove(name: str) -> None:
    try:
        _path(name).unlink()
    except FileNotFoundError:
        pass


def save_store(documents: list[Document], transactions: list[Transaction], source: str) -> None:
    write_json(
        STORE_FILE,
        {
            "source": source,
            "documents": [d.to_dict() for d in documents],
            "transactions": [t.to_dict() for t in transactions],
        },
    )


def load_store() -> tuple[list[Document], list[Transaction], str]:
    raw = read_json(STORE_FILE)
    try:
        docs = [Document.from_dict(d) for d in raw["documents"]]
        txs = [Transaction.from_dict(t) for t in raw["transactions"]]
        return docs, txs, raw.get("source", "")
    except (KeyError, TypeError) as exc:
        raise ObeliskError(f"state file {STORE_FILE} is corrupt: {exc}", EXIT_CORRUPT)
