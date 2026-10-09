# Search syntax and semantics

## Terms
A term is a word made of letters and digits, optionally joined by hyphens (`security-log`).
Terms are case-insensitive. A hyphenated term is indexed both as a whole and as its parts, so
`security` also matches a document containing `security-log`.

## Operators

| Operator | Meaning                                     |
|----------|---------------------------------------------|
| `AND`    | documents matching both sides               |
| `OR`     | documents matching either side              |
| `NOT`    | documents that do **not** match the operand |
| `( )`    | grouping                                    |

Operators must be written in **upper case**; lower-case `and`, `or`, `not` are ordinary terms.
Two operands written next to each other mean `AND`: `royal mint` is `royal AND mint`.

## Precedence

From strongest to weakest binding:

1. parentheses
2. `NOT`
3. `AND` (including implied `AND`)
4. `OR`

Operators of equal strength group from left to right. So:

```
a OR b AND c        means   a OR (b AND c)
NOT a AND b         means   (NOT a) AND b
a AND b OR c        means   (a AND b) OR c
```

## Examples

```
vault AND security
vault OR treasury
(vault OR treasury) AND security
security AND NOT vault
NOT (vault OR treasury) AND audit
royal mint
```

## Ranking
Each matching document scores the sum of the occurrence counts of the query's positive terms
(terms not under a `NOT`) in the document's title, tags and text. Results are ordered by score,
highest first, then by document ID. Ordering is fully deterministic.

## Invalid queries
Empty queries, unbalanced parentheses, operators with a missing operand and unsupported
characters are rejected with exit code 4 and a message on standard error.
