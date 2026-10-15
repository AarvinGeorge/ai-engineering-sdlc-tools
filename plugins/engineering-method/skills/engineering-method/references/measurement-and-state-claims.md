# Measurement and state claims

`superpowers:verification-before-completion` says verify before claiming done. This file covers the
ways a verification lies.

The global measurement rules (proven zeros, fail loudly on an unparseable value, dates read in the
same pass, remote clocks read on the host) apply; this file adds exit codes, state words and labels.

## Exit codes

- `cmd | tail -5` exits with tail's status, not cmd's. A failing suite piped and then `&&`-chained to
  a commit lets the commit through. Use `set -o pipefail`, a wrapper script that exits non-zero, or
  gate explicitly on the summary line (`OK`, `passed`, `0 failed`). Same for `bash -n … | tail`.

## State words

"Deployed", "live", "merged", "parked", "pre-existing", "unchanged since" are measurements.

| Claim | What proves it |
|---|---|
| merged / parked | `git branch --contains <sha>` (parked = no live branch contains it) |
| deployed / live | the sha the running system reports is, or descends from, the commit |
| pre-existing failure | the same test fails on the base commit too |
| unchanged since | a diff or a checksum across the two points, not a memory of them |

A summary written before an event and read after it is the classic trap: a branch recorded as
parked, copied into the next session's notes unchecked, then cited as fact while it was live.

## Labels

Findings carry their basis: **[measured]** (command shown), **[documented]** (page cited),
**[hypothesis]** (neither yet). A hypothesis stated in the tone of a measurement is the failure.
