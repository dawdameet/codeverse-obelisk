"""Query history with undo / redo.

The history is a list of queries plus a cursor pointing at the current one.
Undo and redo move the cursor; running a new query discards anything that
had been undone.
"""

from __future__ import annotations

MAX_ENTRIES = 50


class QueryHistory:
    def __init__(self, states: list[str] | None = None, cursor: int = -1) -> None:
        self.states: list[str] = list(states or [])
        self.cursor = cursor if self.states else -1

    @property
    def current(self) -> str | None:
        return self.states[self.cursor] if self.cursor >= 0 else None

    def push(self, query: str) -> None:
        self.states.append(query)
        if len(self.states) > MAX_ENTRIES:
            del self.states[0]
        self.cursor = len(self.states) - 1

    def undo(self) -> tuple[bool, str | None]:
        """Step back one query. Returns (changed, query now current)."""
        if self.cursor < 0:
            return False, None
        self.cursor -= 1
        return True, self.current

    def redo(self) -> tuple[bool, str | None]:
        if self.cursor + 1 >= len(self.states):
            return False, self.current
        self.cursor += 1
        return True, self.current

    def clear(self) -> None:
        self.states.clear()
        self.cursor = -1

    def to_dict(self) -> dict:
        return {"states": self.states, "cursor": self.cursor}

    @classmethod
    def from_dict(cls, raw: dict) -> "QueryHistory":
        return cls(raw.get("states", []), raw.get("cursor", -1))
