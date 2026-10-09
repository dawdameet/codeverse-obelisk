# Architecture

```
CLI (cli.py)
  |
  +-- ingest.py        read source files into records
  +-- store.py         local JSON state
  +-- indexer.py       inverted index
  +-- query_parser.py  query text -> expression tree -> matching documents
  +-- search.py        run a query, score and shape results
  +-- history.py       query history with undo / redo
  +-- cache.py         bounded query-result cache
  +-- autocomplete.py  prefix suggestions
  +-- transactions.py  transaction table and lookup
  +-- logs.py          log analysis
  +-- bench.py         deterministic autocomplete workload
```

Supporting modules: `config.py` (paths and settings), `errors.py` (exit codes), `models.py`
(records), `tokenizer.py` (shared word splitting), `version.py`.

## Flow of a search

1. `cli.py` builds a cache key from the normalised query.
2. The cache is consulted; on a miss `search.py` asks `query_parser.py` for an expression tree,
   evaluates it against the index, scores and sorts the matches, and stores the result.
3. The query is recorded in the history.

## Design notes

- No global state: each CLI invocation loads the state it needs from disk and saves what it changed.
- Output is deterministic. Nothing visible depends on hash ordering, the clock or randomness.
- Subsystems are independent modules with small interfaces so they can be tested in isolation.
- `OBELISK_HOME` redirects all generated state, which is how the tests stay isolated.
