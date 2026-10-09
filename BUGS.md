# BUGS.md - what is wrong with OBELISK

OBELISK has been misbehaving since the last release. There are **six independent faults**, one
per challenge. Each one is described below by what you can *observe*, not by where it lives -
finding the cause is your job.

- Fix them in **any order**. Each fault is independent of the others.
- A fix lives in a **single file under `src/obelisk/`**, and is usually small. Do not rewrite modules.
- Run `python scripts/run_tests.py` to see the public failing tests (17 of 111 fail at the start).
  Hidden tests also run on the judge, so make the behaviour *correct*, not just green locally.
- Submitting is described in [`contestant-flow.md`](contestant-flow.md).

| ID | Name | Level | Points |
|----|------|-------|--------|
| OB-001 | Vault index integrity | Beginner | 50 |
| OB-002 | Transaction lookup | Easy | 75 |
| OB-003 | Query history | Medium | 100 |
| OB-004 | Query parser | Intermediate | 150 |
| OB-005 | Query cache | Hard | 200 |
| OB-006 | Autocomplete at scale | Elite | 300 |

First run `python obelisk.py ingest` once so there is data to work with.

---

## OB-001 - Vault index integrity

**Symptom.** Valid documents go missing from the index. Records that exist in the vault cannot be
found. It is most visible for the earliest and latest entries, and it depends on how many
documents there are.

**Expected.** Every valid document is in the index and can be found, including the first and last
entries and documents at the edges of an index segment.

**See it yourself.**
```
python obelisk.py index
```
Compare the number of documents with the number that were actually indexed.

**Read about it.** `docs/data-format.md`, `docs/architecture.md`

---

## OB-002 - Transaction lookup

**Symptom.** Some transactions that are definitely stored come back as "not found". Most lookups
in the middle of the ledger work, which makes this easy to miss. The failures cluster at the
boundaries.

**Expected.** Looking up any ID that exists finds it. Looking up an ID that does not exist says so.

**See it yourself.**
```
python obelisk.py transaction TX-10100
python obelisk.py transaction TX-11251
```
Then try other IDs from `data/transactions/transactions.csv`, especially the first and last ones.

**Read about it.** `docs/commands.md`, `docs/data-format.md`

---

## OB-003 - Query history

**Symptom.** The undo feature sometimes puts the session back into the wrong place. It can
restore a query that is not the one you were on, or skip one that was. Several undos in a row, or
an undo followed by a new search, can leave the history in a confusing state.

**Expected.** Each undo returns to exactly the query you were on before the most recent change.
Repeated undos walk back through the history in order until it is empty; undoing an empty history
is harmless.

**See it yourself.**
```
python obelisk.py search aaa --no-cache
python obelisk.py search bbb --no-cache
python obelisk.py search ccc --no-cache
python obelisk.py history undo        # back to bbb
python obelisk.py search ddd --no-cache
python obelisk.py history undo        # which query should you land on now?
python obelisk.py history             # does the list match what you did?
```

**Read about it.** `docs/commands.md`

---

## OB-004 - Query parser

**Symptom.** Some valid compound searches return wrong results. Simple ones are fine. Nested or
mixed expressions can disagree with the documented rules, and two expressions that *should* mean
the same thing do not always agree.

**Expected.** Expressions evaluate exactly as the documented query rules say, including
parentheses and how strongly each operator binds.

**See it yourself.**
```
python obelisk.py search "vault AND security"
python obelisk.py search "vault OR treasury AND security"
python obelisk.py search "NOT vault AND security"
python obelisk.py search "(vault OR treasury) AND security"
```
Work out by hand, from `docs/search.md`, what each of these *should* return, and compare. Try
equivalent spellings of the same query.

**Read about it.** `docs/search.md`

---

## OB-005 - Query cache

**Symptom.** Queries you ran moments ago disappear from the cache while older ones stay. The
cache seems inconsistent when reads and writes are mixed.

**Expected.** The cache holds up to its capacity. When it is full, the entry that has gone the
longest without being used makes room for the new one. Using an entry keeps it alive.

**See it yourself.** (a small cache makes it obvious)
```
export OBELISK_CACHE_SIZE=3          # Windows: set OBELISK_CACHE_SIZE=3
python obelisk.py search a --no-history
python obelisk.py search b --no-history
python obelisk.py search c --no-history
python obelisk.py search a --no-history      # should be a cache hit
python obelisk.py search d --no-history
python obelisk.py cache stats                # which entries are left? is that right?
```

**Read about it.** `docs/commands.md`, `docs/architecture.md`

---

## OB-006 - Autocomplete at scale

**Symptom.** Autocomplete is correct, but it gets dramatically slower as the vocabulary grows.
On small data it is instant; at production size it is unusable.

**Expected.** The suggestions stay correct (same results, same order) *and* the answer stays
fast as the vocabulary grows.

**See it yourself.**
```
python obelisk.py suggest sec
python obelisk.py bench --json
```
`bench` runs a fixed, repeatable workload and reports how long the queries take. Compare the
time with how long you would expect for 500 prefix lookups.

**Read about it.** `docs/architecture.md`, `docs/commands.md`

---

### Reminders

- Only change files under `src/obelisk/`. Anything else is rejected and flagged.
- One bug fix per commit, with `FIX[OB-00X]` in the message.
- A change that breaks other behaviour will fail the hidden regression tests - run the full local
  suite before you submit.
