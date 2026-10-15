# Measurement and state claims

`superpowers:verification-before-completion` says verify before claiming done. This file covers the
ways a verification lies.

## Zeros

- **A zero must be proven able to be non-zero.** A grep once reported zero matches in a week of logs
  because the log had two spaces where the pattern had one; the true figure was fifteen. Run the
  check on a case known to match first, or break the input on purpose and watch it turn red.
- **Fail loudly on an unparseable derived value.** A reachability check run against an empty
  variable reported everything "blocked". Guard every derived input (`: "${VAR:?}"`) before use.

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

## Time

- Never state a date, age or duration not read in the same pass; quote the source (`date`,
  `git log`, a service manager, a container inspect).
- A remote host's clock is read **on that host** (`date -u`), in the same command as the
  time-sensitive query.
- Process uptime is not system age.

## Labels

Findings carry their basis: **[measured]** (command shown), **[documented]** (page cited),
**[hypothesis]** (neither yet). A hypothesis stated in the tone of a measurement is the failure.
