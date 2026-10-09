# Data formats

## Documents (`*.txt`)
A header of `Key: value` lines, a line containing only `---`, then the body text.

```
ID: DOC-0001
Title: Vault door schematic 01
Type: blueprint
Author: agent03
Date: 2025-04-12
Tags: vault, steel, royal
---
Body text ...
```

`ID`, `Title` and `Type` are required and IDs must be unique. Other headers are kept as metadata.
The `Tags` header is searchable along with the title and body.

## Transactions (`*.csv`)
Header row `id,status,amount,date,operator`; IDs look like `TX-10482`. Rows may appear in any
order; OBELISK keeps them ordered by ID number.

## Logs
One record per line: `<timestamp> <LEVEL> <component> key=value ...`. A record needs a `status=`
field; `status=OK` counts as success and any other status as a failure. Lines that do not fit
are counted as malformed.

## Bundled sample data (`data/`)
- `documents/` - 120 documents in five categories
- `transactions/transactions.csv` - 500 transactions
- `logs/ops.log` - 600 log records

`python scripts/generate_sample_data.py` regenerates them byte-for-byte (fixed seed).

## Generated state (`.obelisk-state/`)
JSON files written by OBELISK: `store.json`, `index.json`, `vocab.json`, `history.json`,
`cache.json`. They are derived data and safe to delete.
