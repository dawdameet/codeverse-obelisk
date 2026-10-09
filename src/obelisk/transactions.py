"""Transaction storage and lookup. Records are kept ordered by ID number."""

from __future__ import annotations

import re

from .errors import EXIT_INVALID, EXIT_NOT_FOUND, ObeliskError
from .models import Transaction

_TX_ID = re.compile(r"^TX-(\d+)$", re.IGNORECASE)


def parse_tx_id(raw: str) -> int:
    match = _TX_ID.match(raw.strip())
    if not match:
        raise ObeliskError(
            f"invalid transaction id {raw!r} (expected TX-<number>)", EXIT_INVALID
        )
    return int(match.group(1))


class TransactionTable:
    def __init__(self, transactions: list[Transaction]) -> None:
        self._records = sorted(transactions, key=lambda t: t.number)
        self._numbers = [t.number for t in self._records]

    def __len__(self) -> int:
        return len(self._records)

    def _locate(self, number: int) -> int:
        """Position of ``number`` in the sorted ID list, or -1."""
        numbers = self._numbers
        lo, hi = 0, len(numbers) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if numbers[mid] <= number:
                lo = mid
            else:
                hi = mid
        if numbers and numbers[lo] == number:
            return lo
        return -1

    def find(self, tx_id: str) -> Transaction | None:
        at = self._locate(parse_tx_id(tx_id))
        return self._records[at] if at != -1 else None

    def get(self, tx_id: str) -> Transaction:
        found = self.find(tx_id)
        if found is None:
            raise ObeliskError(f"transaction not found: {tx_id.upper()}", EXIT_NOT_FOUND)
        return found
