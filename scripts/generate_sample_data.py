"""Regenerate the sample dataset in ``data/``.

The output is fully deterministic (fixed seed, own generator), so running this
script on any platform reproduces the files byte-for-byte.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SEED = 20250117


class Rng:
    """Small LCG so output never depends on the interpreter's random module."""

    def __init__(self, seed: int) -> None:
        self.state = seed % (2**32)

    def next(self) -> int:
        self.state = (1664525 * self.state + 1013904223) % (2**32)
        return self.state >> 8

    def below(self, n: int) -> int:
        return self.next() % n

    def pick(self, items):
        return items[self.below(len(items))]

    def sample(self, items, k):
        pool = list(items)
        out = []
        for _ in range(min(k, len(pool))):
            out.append(pool.pop(self.below(len(pool))))
        return out


CATEGORIES = {
    "blueprints": {
        "type": "blueprint",
        "count": 20,
        "titles": ["Vault door schematic", "Press room floor plan", "Die cutting bay layout",
                   "Bullion corridor drawing", "Ventilation shaft plan", "Cable routing diagram",
                   "Smelting hall elevation", "Gatehouse structural sheet"],
        "terms": ["vault", "vault-door", "alloy", "press", "die", "bullion", "corridor", "shaft",
                  "foundation", "steel", "reinforced", "camera-mount", "royal", "mint"],
    },
    "security": {
        "type": "security",
        "count": 30,
        "titles": ["Security review", "Access audit", "Guard rotation brief", "Alarm test report",
                   "Clearance register", "Incident summary", "Perimeter inspection",
                   "Camera coverage assessment"],
        "terms": ["security", "security-log", "security-clearance", "secure", "securing", "guard",
                  "alarm", "camera", "badge", "access", "audit", "vault", "perimeter", "incident",
                  "royal", "mint", "clearance"],
    },
    "personnel": {
        "type": "personnel",
        "count": 20,
        "titles": ["Staff dossier", "Shift roster", "Training record", "Clearance renewal",
                   "Contractor file", "Promotion review"],
        "terms": ["officer", "engineer", "mint-master", "clearance", "security-clearance", "shift",
                  "roster", "training", "contractor", "supervisor", "royal", "mint", "badge"],
    },
    "operations": {
        "type": "operations",
        "count": 30,
        "titles": ["Daily operations log", "Transport manifest", "Maintenance ticket",
                   "Shift handover note", "Inventory count", "Courier schedule",
                   "Equipment status report"],
        "terms": ["inventory", "transport", "courier", "maintenance", "shipment", "coinage",
                  "press", "gold", "silver", "copper", "handover", "schedule", "vault", "royal",
                  "mint", "security-log"],
    },
    "treasury": {
        "type": "treasury",
        "count": 20,
        "titles": ["Treasury ledger extract", "Reserve statement", "Bullion valuation",
                   "Settlement memo", "Audit of reserves", "Transfer authorisation"],
        "terms": ["treasury", "ledger", "reserve", "bullion", "valuation", "settlement", "audit",
                  "gold", "silver", "transfer", "vault", "royal", "mint", "coinage", "security"],
    },
}

FILLER = ["the", "all", "this", "with", "under", "during", "after", "before", "regular", "weekly",
          "annual", "routine", "urgent", "confidential", "restricted", "approved", "pending",
          "reviewed", "completed", "scheduled", "reported", "verified", "recorded", "stored"]

SENTENCES = [
    "The {a} was {f} {b} at the royal mint by the {c} team.",
    "Staff reported that the {a} and the {b} remain {f} under {c} supervision.",
    "A {f} check of the {a} found the {b} consistent with the {c} records.",
    "Access to the {a} is {f}; the {b} must be logged in the {c} register.",
    "The royal mint requires every {a} to be matched against the {b} and the {c}.",
    "During the {f} review the {a} and {c} were compared with the {b}.",
    "Follow-up on the {a}: {b} and {c} are {f} until further notice.",
]

OFFICERS = ["agent01", "agent02", "agent03", "agent04", "agent05", "agent06", "agent07", "agent08"]


def make_documents() -> None:
    rng = Rng(SEED)
    doc_no = 0
    for folder, spec in CATEGORIES.items():
        target = DATA / "documents" / folder
        target.mkdir(parents=True, exist_ok=True)
        for i in range(1, spec["count"] + 1):
            doc_no += 1
            title = f"{spec['titles'][(i - 1) % len(spec['titles'])]} {i:02d}"
            tags = rng.sample(spec["terms"], 3)
            sentences = []
            for _ in range(4 + rng.below(4)):
                sentences.append(
                    rng.pick(SENTENCES).format(
                        a=rng.pick(spec["terms"]),
                        b=rng.pick(spec["terms"]),
                        c=rng.pick(spec["terms"]),
                        f=rng.pick(FILLER),
                    )
                )
            sentences.append(f"Reference marker: marker{doc_no:04d}.")
            month = 1 + rng.below(12)
            day = 1 + rng.below(28)
            header = [
                f"ID: DOC-{doc_no:04d}",
                f"Title: {title}",
                f"Type: {spec['type']}",
                f"Author: {rng.pick(OFFICERS)}",
                f"Date: 2025-{month:02d}-{day:02d}",
                f"Tags: {', '.join(tags)}",
                "---",
            ]
            name = f"{folder[:-1] if folder.endswith('s') else folder}-{i:02d}.txt"
            text = "\n".join(header + [" ".join(sentences)]) + "\n"
            (target / name).write_text(text, encoding="utf-8", newline="\n")


def make_transactions() -> None:
    rng = Rng(SEED + 1)
    statuses = ["CLEARED", "CLEARED", "CLEARED", "PENDING", "REJECTED", "FLAGGED"]
    lines = ["id,status,amount,date,operator"]
    tx = 10000
    for _ in range(500):
        tx += 1 + rng.below(4)
        amount = f"{rng.below(900000) / 100 + 10:.2f}"
        date = f"2025-{1 + rng.below(12):02d}-{1 + rng.below(28):02d}"
        lines.append(f"TX-{tx},{rng.pick(statuses)},{amount},{date},{rng.pick(OFFICERS)}")
    out = DATA / "transactions"
    out.mkdir(parents=True, exist_ok=True)
    (out / "transactions.csv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def make_logs() -> None:
    rng = Rng(SEED + 2)
    levels = ["INFO", "INFO", "INFO", "WARN", "ERROR"]
    components = ["vault-gate", "press-line", "audit-service", "courier-link", "alarm-grid"]
    ops = ["unlock", "inspect", "transfer", "calibrate", "dispatch", "verify"]
    statuses = ["OK", "OK", "OK", "OK", "FAIL", "DENIED", "TIMEOUT"]
    lines = []
    for n in range(600):
        stamp = f"2025-03-{1 + n // 24:02d}T{n % 24:02d}:{rng.below(60):02d}:{rng.below(60):02d}Z"
        lines.append(
            f"{stamp} {rng.pick(levels)} {rng.pick(components)} op={rng.pick(ops)} "
            f"status={rng.pick(statuses)} user={rng.pick(OFFICERS)} ms={10 + rng.below(900)}"
        )
    out = DATA / "logs"
    out.mkdir(parents=True, exist_ok=True)
    (out / "ops.log").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    make_documents()
    make_transactions()
    make_logs()
    print("sample data written to", DATA)
    return 0


if __name__ == "__main__":
    sys.exit(main())
