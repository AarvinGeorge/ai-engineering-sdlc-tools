# The progress ladder

The standing way to show progress on tier c work, without being asked; at any other tier, on
request. It answers in one
screen: where the work is, what it cost, what it found, and what is waiting on the person. Prose
buries all four.

## When

When a task lands, when lanes merge, when anything is pushed or deployed, and whenever asked.

## Shape (one fenced monospace block)

1. **Title line:** work name · branch · plan document · base commit and what it is · whether a goal
   is active · `state` at the right.
2. **A rule, then numbered rows in build order.** Each row: what it does in plain words, a six-block
   bar (`██████` done, `███░░░` running, `░░░░░░` not started), and `DONE <sha>`, `running`, or a
   short state.
3. **Indented sub-bullets** under a row for what a review found or what a task carries, each with its
   own bar when it has a state of its own.
4. **A section rule with a phrase** whenever the work changed shape, so the reader sees why the list
   grew.
5. **Footer:** suite numbers measured in this pass; the invariant that is load-bearing; the live
   state of each environment; and the decisions waiting on the person, numbered, each marked given
   or not given.

Every number comes from a run in the same pass. A commit is named by its sha. Drop footer lines that
do not apply (a tier a task has no environments).

## Example

```
EXPORT CSV · branch export-csv · plan docs/14 · base 3f2a91c (main) · no goal          state
──────────────────────────────────────────────────────────────────────────────────────────
1  failing tests for the three export shapes             ██████  DONE 7c1e04b
2  exporter streams rows instead of building a list      ██████  DONE a90d3f2
   · review (other model): quoted newline breaks a row    ██████  fixed 1b77e20
3  download endpoint with a size cap                     ███░░░  running
──── reopened 14:20: review found the cap is per-request, not per-user ────
4  per-user cap, one shared check at both exits          ░░░░░░  not started
──────────────────────────────────────────────────────────────────────────────────────────
SUITES   unit 212 passed, 0 failed (pytest -q, 14:31 UTC)   integration not run
INVARIANT  no export holds the whole table in memory
LIVE     production 9e04c11, unchanged · staging a90d3f2
YOURS    1. cap value: 50 MB per user/day — not given
         2. ship behind no flag (on for everyone) — given 13:05
```
