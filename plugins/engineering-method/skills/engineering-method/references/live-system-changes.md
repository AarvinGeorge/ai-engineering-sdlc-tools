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
| Back up the state the change touches, then verify the backup | A backup not read back is a hope; a code-only change records the rollback revision instead and says so. |
| Prove before production | On a laptop, a throwaway container, or a separate test stack. Never run a test suite inside the live system (a guard test enforces it; below). |
| No secrets in artifacts | Name a credential, never its value — not in documents, commits or transcripts. |

## The deploy standard

One living standard file (e.g. `DEPLOYING.md`) and one template (e.g. `DEPLOY-TEMPLATE.md`). Every release
gets its own file copied from the template, every placeholder filled, nothing deleted.

**The guard idea:** the standard carries a machine-readable list of required step ids, and a test in
the normal suite fails if any deploy file is missing a step, has them out of order, or still holds a
placeholder. The method is enforced by the suite, not by memory.

The template's sections, in order — adapt the content, keep the shape:

1. **Preconditions** — what must be true before starting, each with the command that checks it.
2. **Backup, verified** — snapshot the state the change touches; read it back. A code-only change (no data, schema or config touched, checked against the diff) records the running revision as the rollback point instead.
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

## The deploy file is code

- **Reviewed by a different model, and every command block dry-run on the bench before that
  review.** *Why:* the first bench runs of one release stopped on faults in the deploy file, not in
  the product. *Test:* the record shows each block's bench run and names the reviewer's model.
- **It executes nothing inside a live container.** Tests run on a laptop, in a throwaway started
  from the release image, or on the bench; the live system only receives the tested artifact.
  *Why:* a suite run inside production can write, send or lock what real people use. *Test:* a guard
  test in the normal suite fails on any deploy-file step that runs a test, a shell or an ad hoc
  script inside the live container (`docker exec <live> pytest …`), and a planted violation turns it
  red.
- **Re-read against the final head before each gate.** *Why:* a fix round after the file was written
  changes what it must check. *Test:* the gate record names the head the file was re-read against.

## Proving a release

1. **Rehearse the procedure, not only the code.** The bench runs the same deploy file, the same
   commands, on a production-shaped target. *Why:* a bench that proved the code let the steps fail
   live. *Test:* the bench record and the production record follow one file.
2. **Expected state is recorded by machine.** Flags, plugin counts, image ids and config hashes that
   a read-back compares against are written by a script from the release, never typed. *Why:*
   hand-kept lists went stale between releases. *Test:* every expected value names the command that
   produced it.
3. **A read-only check against live right before the switch.** The pre-switch gate compares the
   running system with what the deploy file assumes (running revision, image ids, config hash);
   any mismatch stops. *Why:* live drifts between the plan and the switch. *Test:* the gate's output
   sits immediately before the switch command in the record.
4. **Recovery is read back like a deploy.** A rollback gets the same read-backs as the forward
   path. *Why:* a rollback trusted without a health read is a second unverified change. *Test:* the
   rollback section lists its read-backs.
5. **A repeat fault needs a mechanism fix.** The second time a step fails the same way, change the
   mechanism (a script, a guard, a template field), not the operator's care. *Why:* the same slip
   returned in three releases while each was fixed by hand. *Test:* the second occurrence's record
   names the mechanism changed.
6. **Smoke never shrinks for what a change touches.** Every path the diff touches has a smoke case,
   and each case asks for a fresh, observable reply (on a persistent session, ask something new).
   *Why:* a smoke ask that wanted no reply passed while the path was broken. *Test:* the smoke list
   maps each touched path to a case.
7. **Test once, promote the artifact.** The build that passed (by digest) is the one promoted; never
   rebuild for production. *Why:* a rebuild is an untested artifact with a tested name. *Test:* the
   running digest equals the tested digest, read from both.
8. **Real-model benches before production.** Golden tests with a faked model pin behaviour cheaply,
   but they cannot show timing, retries or a state machine meeting a real model's second pass; a
   bench with the real model can. *Why:* a fix green on every golden looped on the first real bench
   because the model kept writing after the turn had ended. *Test:* the gate lists the real-model
   bench cases and their results.
9. **The pipeline, in order:** build → cross-model review → full suite → bench → gate → production
   → watch → limited bench → wider rollout. A red stage holds the release where it is; holding needs
   no one's permission, promoting does. *Test:* the promotion grid (progress-ladder.md) shows every
   release on every stage.

## Pushing and backups

- **Back up to the remote after each recorded step, never by force, behind a pre-push guard.** The
  guard scans every outgoing commit for secrets and for protected personal data, and refuses the
  push on a hit. *Why:* work only on a laptop is one disk from lost, and a push is permanent.
  *Test:* the guard is installed as the pre-push hook, and a control run with a planted fake value
  shows it refusing (a scan that has never fired is not shown able to).
- **Never push tags or refs that preserve rewritten history.** Push branches (`git push origin
  --all`), not `--tags` or `--mirror`, when a rewrite removed data. *Why:* one backup tag re-publishes
  everything the rewrite removed. *Test:* `git ls-remote --tags origin` after the push lists none of
  them.

## Pipeline and judgement

Gates are deterministic and decide pass or fail. An agent's role on a red gate is to investigate and
propose: gather the log, the failing case, the diff since the last green, and the traces. It never
loosens a gate, deletes a case, raises a threshold, re-runs until green, or deploys on its own.
