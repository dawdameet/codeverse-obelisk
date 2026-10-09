# Command reference

All commands accept `--json` (stable, machine-readable output). Human-readable output is the default.

## ingest `[path]`
Recursively reads documents (`*.txt`) and transaction tables (`*.csv`) below `path`
(default: the bundled `data/` directory), stores them in the local state directory and builds
the search index and the autocomplete vocabulary. Files that cannot be parsed are reported under
`Errors`; the rest of the data is still ingested.

## inspect `<document-id>`
Shows a stored document: ID, title, type, source, metadata and a text preview.

## search `<query>` `[--limit N] [--no-cache] [--no-history]`
Searches the index. See [search.md](search.md) for the query syntax. Results are ranked by
relevance score, highest first; ties are ordered by document ID. Each search is recorded in the
query history (unless `--no-history`) and its result may be served from the query cache
(unless `--no-cache`). The output ends with `Cache: HIT`, `MISS` or `BYPASSED`.

## history `[list|undo|redo|clear] [--run]`
Manages the query history.

- `list` (default) prints the recorded queries; `>` marks the current one.
- `undo` steps back to the previous query state; `redo` steps forward again.
- Running a new search after an undo discards the queries that had been undone.
- `clear` empties the history.
- `--run` re-runs the restored query.

## suggest `<prefix>` `[--limit N]`
Autocomplete over the indexed vocabulary. Suggestions are ranked by how often the term occurs in
the data (most frequent first), ties broken alphabetically. Matching is case-insensitive.

## transaction `<TX-id>`
Looks up a transaction. IDs have the form `TX-<number>`; the lookup is case-insensitive.

## cache `[stats|clear]`
Shows cache statistics (capacity, size, hits, misses, evictions and the entries from most to
least recently used) or clears the cache. The default capacity is 5 entries; set the
`OBELISK_CACHE_SIZE` environment variable to change it. The cache policy is **least recently
used**: reading or writing an entry makes it the most recently used, and when the cache is full
the entry that has gone unused the longest is evicted.

## logs `[file]`
Analyses an operational log (default: `data/logs/ops.log`): totals, successful/failed
operations, malformed lines and counts per level, status, component, operation and user.

## status
Shows index state and counts of documents, transactions, vocabulary terms and cache usage.

## index
Rebuilds the search index from the stored documents and reports how many were indexed.

## rebuild
Rebuilds all derived state (index, vocabulary) and empties the cache. Source data and the query
history are untouched.

## bench `[--vocab N] [--queries N] [--seed N] [--limit N]`
Runs a deterministic autocomplete workload against a synthetic vocabulary and prints a checksum
of the answers plus timing. Identical arguments always give an identical checksum.

## Exit codes

| Code | Meaning                                              |
|------|------------------------------------------------------|
| 0    | success                                              |
| 1    | unexpected failure                                   |
| 2    | usage error (unknown command, bad arguments)         |
| 3    | not found (document, transaction, file or path)      |
| 4    | invalid query or argument value                      |
| 5    | corrupt or unreadable data                           |
| 6    | no index/state yet - run `ingest` first              |

Errors are printed to standard error as `obelisk: error: <message>`; stack traces are never shown
for expected failures.

## Environment variables

| Variable             | Purpose                                     |
|----------------------|---------------------------------------------|
| `OBELISK_HOME`       | directory for generated state               |
| `OBELISK_DATA_DIR`   | directory ingested when no path is given    |
| `OBELISK_CACHE_SIZE` | query cache capacity (default 5)            |
