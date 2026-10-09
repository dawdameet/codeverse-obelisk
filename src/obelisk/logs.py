"""Operational log analysis."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .errors import EXIT_NOT_FOUND, ObeliskError

_LINE = re.compile(r"^(\S+)\s+(\w+)\s+(\S+)\s*(.*)$")
_FIELD = re.compile(r"(\w+)=(\S+)")
SUCCESS_STATUS = "OK"


def _ordered(counter: Counter) -> dict:
    return dict(sorted(counter.items(), key=lambda kv: (-kv[1], kv[0])))


def analyse(path: Path) -> dict:
    if not path.is_file():
        raise ObeliskError(f"log file not found: {path}", EXIT_NOT_FOUND)
    levels, components, statuses, operations, users = (Counter() for _ in range(5))
    total = ok = failed = malformed = 0
    total_ms = timed = 0
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            match = _LINE.match(line)
            fields = dict(_FIELD.findall(match.group(4))) if match else {}
            if not match or "status" not in fields:
                malformed += 1
                continue
            total += 1
            levels[match.group(2)] += 1
            components[match.group(3)] += 1
            statuses[fields["status"]] += 1
            operations[fields.get("op", "-")] += 1
            users[fields.get("user", "-")] += 1
            if fields["status"] == SUCCESS_STATUS:
                ok += 1
            else:
                failed += 1
            if fields.get("ms", "").isdigit():
                total_ms += int(fields["ms"])
                timed += 1
    return {
        "file": path.name,
        "total": total,
        "successful": ok,
        "failed": failed,
        "malformed": malformed,
        "avg_ms": round(total_ms / timed, 2) if timed else 0,
        "by_level": _ordered(levels),
        "by_status": _ordered(statuses),
        "by_component": _ordered(components),
        "by_operation": _ordered(operations),
        "by_user": _ordered(users),
    }
