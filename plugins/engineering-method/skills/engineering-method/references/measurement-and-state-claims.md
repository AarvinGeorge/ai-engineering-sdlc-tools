# Measurement and state claims

`superpowers:verification-before-completion` says verify before claiming done. This file covers the
ways a verification lies.

The global measurement rules (proven zeros, fail loudly on an unparseable value, dates read in the
same pass, remote clocks read on the host) apply; this file adds exit codes, suite results, negatives and time, state words and labels.

## Exit codes

- `cmd | tail -5` exits with tail's status, not cmd's. A failing suite piped and then `&&`-chained to
  a commit lets the commit through. Use `set -o pipefail`, a wrapper script that exits non-zero, or
  gate explicitly on the summary line (`OK`, `passed`, `0 failed`). Same for `bash -n … | tail`.
- **Under `pipefail`, `producer | grep -q` can fail falsely:** `grep -q` exits at the first match,
  the producer gets SIGPIPE, and the pipe reports failure. Count matches instead
  (`n=$(producer | grep -c pattern)`). *Test:* a strict-mode check with a match returns success.
- **A switch that reads only some truthy words fails silently.** If a setting accepts `1`, `true`
  and `yes`, then `on` means off. *Test:* each switch's accepted values are written beside it, and a
  read-back shows the feature on.

## Suite results

- **Builders run the full suite once before reporting, not only the touched modules.** *Why:* in one
  merge, runs of the touched modules alone missed five failures elsewhere. *Test:* the report quotes
  the full suite's summary line, once; a long run is not looped.
- **The controller's suite runs inside the project tree.** *Why:* tests that read the repository
  layout skip themselves when run from a copy or another directory, and a green with silent skips
  tested less than it says. *Test:* the report shows the directory and command the suite ran from.
- **A skip count is a measurement.** Report passed, failed and skipped; a change in skips from the
  base is explained before the result is trusted. *Why:* a rise in skips looks like a pass. *Test:*
  the base and head skip counts both appear, and any difference has a named cause.
- **"Is this a regression?" is settled by a base check against what production runs.** Run the same
  check on the revision live today: failing on both is pre-existing (its own backlog item); failing
  only on the head is a regression and stops the release. *Why:* without the base run, both "it was
  already broken" and "we broke it" are guesses. *Test:* both runs are shown, with their revisions.

- **A flaky timing test is fixed by measuring better, not by loosening the limit.** Take the best of
  N runs against the same limit. *Why:* a raised limit stops catching the slowdown it was written
  for. *Test:* the limit is unchanged in the diff.

## Negatives and time

- **A negative carries its window.** Write "not seen as of 18:00 UTC; the window closes 22:00 UTC",
  then re-read after the close. *Why:* an absence logged early is later believed as fact; it is the
  proven-zero rule applied to time. *Test:* every "did not happen" names when it was read and when
  its window closes.
- **Timestamps come from the clock, never from estimation.** *Why:* guessed times were caught by
  gates (a plan stamped in the future, a log entry stamped minutes ahead of when it was written).
  *Test:* each time in a record was read from a clock in that pass; a wrong one is corrected by a new
  entry, not an edit.

## State words

"Deployed", "live", "merged", "parked", "pre-existing", "unchanged since" are measurements.

| Claim | What proves it |
|---|---|
| merged / parked | `git branch --contains <sha>` (parked = no live branch contains it) |
| deployed / live | the sha the running system reports is, or descends from, the commit |
| pre-existing failure | the same test fails on the base commit too (for a release: on what production runs) |
| unchanged since | a diff or a checksum across the two points, not a memory of them |

A summary written before an event and read after it is the classic trap: a branch recorded as
parked, copied into the next session's notes unchecked, then cited as fact while it was live.

## Labels

Findings carry their basis: **[measured]** (command shown), **[documented]** (page cited),
**[hypothesis]** (neither yet). A hypothesis stated in the tone of a measurement is the failure.
