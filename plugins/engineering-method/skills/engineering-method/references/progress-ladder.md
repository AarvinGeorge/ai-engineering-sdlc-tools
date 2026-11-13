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
5. **Footer:** suite numbers measured in this pass (passed, failed, skipped); the invariant that is
   load-bearing; the live state of each environment; the caveat line (what is NOT yet fixed); and
   the decisions waiting on the person, numbered, each marked given or not given.

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
SUITES   unit 212 passed, 0 failed, 3 skipped (pytest -q in repo root, 14:31 UTC; base 3 skipped)
         integration not run
INVARIANT  no export holds the whole table in memory
LIVE     production 9e04c11, unchanged (GET /version, 14:32 UTC) · staging a90d3f2
CAVEAT   NOT yet fixed: the cap resets at UTC midnight, not the user's midnight (row 4 does not cover it)
YOURS    1. cap value: 50 MB per user/day — not given
         2. ship behind no flag (on for everyone) — given 13:05
```

## The promotion pipeline grid

The ladder shows one piece of work; the grid shows every release on every stage of the promotion
pipeline (live-system-changes.md, "Proving a release"). **Shown with every progress report** on
work that promotes releases, directly under the ladder.

- **One row per release** (`R-NN`, with the story it ships), one column per stage: build,
  cross-model review, full suite, bench, gate, production, watch, limited bench, wider rollout.
- **Marks:** `✓` passed, `✗` failed, `·` not reached. A release held at a stage reads `✗→held` and
  every stage after it stays `·`.
- **Under each row:** the build commit under the release id, and the time each stage finished
  (UTC; the date of the first stage is in the title line, and the times run forward from it, so a
  smaller time than the one before it is the next day). A stage that ran on a different commit from the build shows
  that commit in its cell instead, and that is a finding.
- **A note under a held release** saying where it is held, why, and what releases it.
- **Read, never recalled:** every mark and time comes from the deployment ledger and the stage
  records in the same pass, and the title line says when and from what.

```
PROMOTION · read 14 Mar 14:05 UTC from ledger + stage records
               build   review  full    bench   gate    prod    watch   limited rollout
R-01 E-01.S1   ✓       ✓       ✓       ✓       ✓       ✓       ✓       ✓       ·
     4be20c1   10:02   11:40   12:15   14:58   15:12   19:25   20:26   01:07
R-02 E-02.S1   ✓       ✓       ✓       ✓       ✓       ✓       ✓       ✓       ·
     9d07a3e   22:10   23:30   00:05   02:40   03:07   03:49   04:50   06:16
R-03 E-02.S2   ✓       ✓       ✓       ✗→held  ·       ·       ·       ·       ·
     c81f5b2   07:55   09:40   10:20   11:01
     HELD at bench: the real model wrote after the turn had ended and a follow-up was sent;
     fix in re-review, then the bench re-runs. Production stays on R-02.
```

## Making a report honest

- **Every number from a run in the same pass.** Counts, times and suite results are read now, with
  the command; a figure carried from an earlier report is labelled with its time or dropped. *Why:*
  a carried number reads as a fresh one. *Test:* each number has its command or its time.
- **State words beside the command that proved them.** "Live 9e04c11 (GET /version, 14:32 UTC)",
  never "live" alone (measurement-and-state-claims.md). *Why:* a bare "live" is a memory in the tone
  of a measurement. *Test:* no state word stands alone.
- **The caveat line.** Say what is NOT yet fixed, and anything claimed earlier that the diff does
  not contain. *Why:* a report of fixes with no caveat line read as "all fixed" while two roots were
  untouched and one claimed change was 0 lines of the diff. *Test:* the footer has a CAVEAT line,
  even when it says "none known".
- **The person's decisions, numbered, given or not given.** Each with the time it was given. *Why:*
  an unnumbered ask waits silently, and a remembered "yes" gets assumed. *Test:* every given
  decision carries its time.
