"""Plain data records shared across subsystems."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Document:
    id: str
    title: str
    type: str
    source: str  # path relative to the ingested root, with forward slashes
    metadata: dict = field(default_factory=dict)
    text: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict) -> "Document":
        return cls(
            id=raw["id"],
            title=raw["title"],
            type=raw["type"],
            source=raw["source"],
            metadata=dict(raw.get("metadata", {})),
            text=raw.get("text", ""),
        )


@dataclass
class Transaction:
    id: str
    status: str
    amount: str
    date: str
    operator: str

    @property
    def number(self) -> int:
        return int(self.id.split("-", 1)[1])

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict) -> "Transaction":
        return cls(**raw)
