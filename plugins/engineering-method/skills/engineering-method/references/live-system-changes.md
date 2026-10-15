# Changes to a live system (tier c)

Applies whenever real people use the system today. Proven practice: change management, a written
runbook per release, and a rollback planned before the change rather than invented during the
outage.

## Standing rules

| Rule | Detail |
|---|---|
| Read-only by default | Inspection, logs, config reads, benchmarks need no permission. |
| Ask before mutating | Config edits, restarts, scheduled-job changes, installs, credential changes: state what changes and how to undo it. |
| Never restart blind | Check for in-flight work first; re-read it after any wait or build. |
| Back up, then verify the backup | A backup not read back is a hope. |
| Prove before production | On a laptop, a throwaway container, or a separate test stack. Never run a test suite inside the live system. |
| No secrets in artifacts | Name a credential, never its value — not in documents, commits or transcripts. |

## The deploy standard

One living standard file (`DEPLOYING.md`) and one template (`DEPLOY-TEMPLATE.md`). Every release
gets its own file copied from the template, every placeholder filled, nothing deleted.

**The guard idea:** the standard carries a machine-readable list of required step ids, and a test in
the normal suite fails if any deploy file is missing a step, has them out of order, or still holds a
placeholder. The method is enforced by the suite, not by memory.

The template's sections, in order — adapt the content, keep the shape:

1. **Preconditions** — what must be true before starting, each with the command that checks it.
2. **Backup, verified** — snapshot the state the change touches; read it back.
3. **Build and test off the live system** — merge, full suites, image build and its own suite.
4. **Bring the target up to date** — fetch, config regenerated from source (never hand-merged).
5. **Red against the old** — the new checks run against the old system first and fail, proving
   they can fail.
6. **In-flight window, then switch** — read in-flight work; the last read is the last command
   before the switch.
7. **Read-backs** — named checks against the new system, each turning green.
8. **Push and record** — remotes, the running revision recorded from the system itself.
9. **Acceptance** — the real-use check, from the user's seat where possible.
10. **Rollback** — the exact commands and the trigger that fires them, written before step 1.
11. **Known limits, stated.**
12. **Record** — decision log, plan state, index.

**Stop and report** if a precondition fails, a red check is green against the old system, or a
read-back fails: do not improvise past the file.

## Pipeline and judgement

Gates are deterministic and decide pass or fail. An agent's role on a red gate is to investigate and
propose: gather the log, the failing case, the diff since the last green, and the traces. It never
loosens a gate, deletes a case, raises a threshold, re-runs until green, or deploys on its own.
