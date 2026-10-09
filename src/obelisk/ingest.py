"""Reading the source dataset: documents, transactions, and log files."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from .errors import EXIT_NOT_FOUND, ObeliskError
from .models import Document, Transaction

DOCUMENT_SUFFIXES = {".txt"}
REQUIRED_HEADERS = ("id", "title", "type")


@dataclass
class IngestResult:
    documents: list[Document] = field(default_factory=list)
    transactions: list[Transaction] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    files: int = 0


def parse_document(path: Path, root: Path) -> Document:
    """Parse one document file: ``Key: value`` header, ``---``, then body."""
    raw = path.read_text(encoding="utf-8")
    header_part, sep, body = raw.partition("\n---\n")
    if not sep:
        raise ValueError("missing '---' separator between header and body")
    headers: dict[str, str] = {}
    for line in header_part.splitlines():
        if not line.strip():
            continue
        key, colon, value = line.partition(":")
        if not colon:
            raise ValueError(f"malformed header line: {line!r}")
        headers[key.strip().lower()] = value.strip()
    for required in REQUIRED_HEADERS:
        if not headers.get(required):
            raise ValueError(f"missing required header '{required}'")
    metadata = {
        k: v for k, v in headers.items() if k not in REQUIRED_HEADERS
    }
    return Document(
        id=headers["id"],
        title=headers["title"],
        type=headers["type"].lower(),
        source=path.relative_to(root).as_posix(),
        metadata=metadata,
        text=body.strip(),
    )


def parse_transactions(path: Path) -> list[Transaction]:
    with open(path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for line_no, row in enumerate(reader, start=2):
            try:
                tx = Transaction(
                    id=row["id"].strip().upper(),
                    status=row["status"].strip().upper(),
                    amount=row["amount"].strip(),
                    date=row["date"].strip(),
                    operator=row["operator"].strip(),
                )
                tx.number  # validates the TX-<number> format
            except (KeyError, ValueError, AttributeError, IndexError):
                raise ValueError(f"{path.name} line {line_no}: malformed transaction row")
            rows.append(tx)
    return rows


def ingest_path(root: Path) -> IngestResult:
    """Recursively ingest everything supported below ``root``."""
    if not root.exists():
        raise ObeliskError(f"path does not exist: {root}", EXIT_NOT_FOUND)
    result = IngestResult()
    if root.is_file():
        files, base = [root], root.parent
    else:
        files, base = sorted(p for p in root.rglob("*") if p.is_file()), root
    seen_ids: set[str] = set()
    for path in sorted(files, key=lambda p: p.relative_to(base).as_posix()):
        rel = path.relative_to(base).as_posix()
        try:
            if path.suffix.lower() in DOCUMENT_SUFFIXES:
                doc = parse_document(path, base)
                if doc.id in seen_ids:
                    raise ValueError(f"duplicate document id {doc.id}")
                seen_ids.add(doc.id)
                result.documents.append(doc)
                result.files += 1
            elif path.suffix.lower() == ".csv":
                result.transactions.extend(parse_transactions(path))
                result.files += 1
        except (ValueError, UnicodeDecodeError, OSError) as exc:
            result.errors.append(f"{rel}: {exc}")
    result.documents.sort(key=lambda d: d.id)
    result.transactions.sort(key=lambda t: t.number)
    return result
