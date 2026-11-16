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

## The release tree

When a release spans several tasks, or the person asks where a release stands, the ladder's rows
are a tree in the naming hierarchy (docs-and-decisions.md, "Names"), not a flat list. Its parts, in
order:

1. **Epic → story → task**, indented, each with its plain-words name beside its id.
2. **On each task:** builder model → reviewer model, its state and commit.
3. **The active row marked** (`▶`).
4. **Each review round indented** under its task (round, verdict, fix commit).
5. **Parked items with their home** (the epic or story that now owns them).
6. **The stages still to come**, after the last one passed (gate, production, watch, limited bench,
   wider rollout), from the promotion grid below.

```
R-12 · E-07 Team calendars (shared rota per team) · read 09:40 from the plan and deploy log
E-07.S1 rota view → R-12
  T1 rota table and API            m1 → m2    DONE 3c9e1a0
     · review r1: 2 Minor — fixed 7f2b5d4
▶ T2 week grid in the web app      m1 → m2    in progress
     · review r1: Important (time zone of the week start), fix in progress
  T3 export to calendar file       m1 → m2    not started
E-07.S2 swap requests              PARKED → home: E-09 (notifications epic)
Stages: build (T2, T3 open) · review · suite · bench · gate · production · watch · rollout
```

*Why:* a flat list hid where each task sat. *Test:* every task line names builder and reviewer, and
the stages after the current one are listed.

## An update that stands on its own

An update to someone who was not in the session (an owner, a team) is read cold. Its shape:

1. **"Needs you" first:** each open decision, numbered, with its options and the deadline it
   gates. Nothing comes before it, not even a correction or a note to the person who asked: those
   go after the update.
2. **Each item gets a plain gloss:** its plain meaning, its importance, where it sits, and a "since
   <time>:" clause saying what changed since the last update (name that update's time).
3. **A source for every fact:** "(deploy log, read 09:40 UTC)", "(incident list, four entries
   counted one by one)". Counts are read entry by entry (measurement-and-state-claims.md, "Counts"); a figure that
   corrects an earlier one says so.
4. **No bare id.** Every `E-07.S1`, `R-12`, `T2` has its plain meaning beside it, every time it
   first appears in a section.
5. **Status verbs in plain meaning:** "ran on the bench and came through clean", never "benched"; "on hold
   at the gate", never "gated". A word copied from the ledger is rewritten if a stranger would read
   it differently.

*Why:* the owner lost context across many concurrent items, and a jargon verb read as its opposite.
*Test:* the first block is the decisions; no id stands without its gloss; each number has a source.

## A checklist the person runs

While a person works through a numbered step list (a migration, a setup), each reply that follows a
progress report is this, in order:

1. **Next step, at the top:** "Next: step N — <what it does>" (the lowest unticked step that is
   not blocked).
2. **The whole list, reprinted**, every step, each with `[x]` done or `[ ]` not done, the original
   numbers and the commands in place, grouped under where they run (laptop, console, server).
3. **Tick only what was reported done or measured.** An expectation that a step will work, or
   that it matches an earlier one, is not a report: the step stays `[ ]`, with a one-line note on
   how to check it.
4. **A new step keeps the numbering:** insert it as `6a`, never renumber; a step done out of order
   is ticked where it sits.
5. **Notes after the list**, short: what failed and how it was fixed, what to check.

```
Next: step 3 — turn on the new sign-up form for 10% of visitors

In the repository (your laptop)
  [x] 1. make release VERSION=2.4.0
  [x] 2. ./scripts/smoke.sh --target staging
In the feature-flag console
  [ ] 3. Set signup_v2 to 10%
  [ ] 4. Watch the sign-up error chart for 30 minutes
In the analytics console
  [x] 5. Create the "signup_v2 completions" dashboard   (done early)
  [ ] 6. Compare completions against the old form after a day
```

*Why:* steps were lost while the person switched between consoles, and a reply with only the next
step dropped the rest. *Test:* every original step appears with its number, and only reported steps
are ticked. Plan-layer's task columns are the same idea for the planning page.

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
PROMOTION · from 2 Mar · read 4 Mar 09:00 UTC from the ledger and stage records
               build   review  full    bench   gate    prod    watch   limited rollout
R-01 E-01.S1   ✓       ✓       ✓       ✓       ✓       ✓       ✓       ✓       ·
     5a1e3d0   08:10   09:05   09:40   10:30   11:00   11:45   12:45   16:20
R-02 E-02.S1   ✓       ✓       ✓       ✓       ✓       ✓       ✓       ✓       ·
     b72c9f4   17:00   18:15   18:50   20:10   20:30   21:05   22:05   02:30
R-03 E-02.S2   ✓       ✓       ✓       ✗→held  ·       ·       ·       ·       ·
     e03d8a6   06:40   07:30   08:05   08:45
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
