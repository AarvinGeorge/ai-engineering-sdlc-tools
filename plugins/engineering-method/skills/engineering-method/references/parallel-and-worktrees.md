# Parallel work and worktrees

`superpowers:dispatching-parallel-agents` and `using-git-worktrees` say how. This file says when, and
who may write.

## The parallel test

Two questions: **do the two pieces of work touch the same file region, and does either depend on the
other's output?** Both no: run them at once. Either yes: run them in order. Three interdependent
plans built in parallel once produced two Criticals that were purely "my sibling moved", and the fix
cost more than the parallelism saved.

| Shape | Verdict |
|---|---|
| Plan revisions, reviews, research, docs — different files, read-only or one file each | parallel |
| Implementers on separate branches, different regions | parallel, with a named merge order |
| Implementers on one branch | serial |
| One plan calls the other's new function | serial, callee first |
| A review of work still being written | serial, wait for the head to settle |

When the test passes, parallel is the default: separate worktrees, a review per lane, the suites
after each merge. Each lane carries a review, so count that cost; when the test fails, run serial.

## Bottleneck first

The industry baseline is Kanban's work-in-progress limit and the Theory of Constraints: the
throughput of the whole is the throughput of its tightest stage, and here that stage is usually the
strongest reviewer. When a release is held (blocked at a stage):

1. **The held release goes first and alone.** The day starts with what unblocks it (the fix's
   re-review, the bench re-run, the gate), and no other work claims that reviewer until it clears. *Why:* five lanes once ran while one release sat blocked, and the
   strongest reviewer ran out of its weekly limit before the release was cleared. *Test:* the plan's
   first rows are the held release's stages, and no other row claims its reviewer before the gate.
2. **New lanes wait.** Do not start lanes whose reviews compete for that reviewer while the release
   is held; state the cap as "lanes = reviews the remaining capacity can carry", which is often zero
   until the reset. Building now and reviewing "later" is the same queue with more work waiting in
   it. *Why:* work in progress past the review capacity only lengthens lead time (DORA). *Test:* the
   plan says how many lanes start and the capacity figure behind that number.
3. **No whole-branch review while it is held.** The held release gets a delta re-review only
   (review-loop.md, "Fix rounds"); a whole-branch pass waits until the release is through. *Test:*
   no whole-branch review sits in the plan before the held release's gate.
4. **Repeated stops change the procedure.** The second stop of the same kind at one stage changes
   the mechanism that let it through (live-system-changes.md, "Proving a release", item 5).

Review capacity is read, not guessed: model-routing-and-cost.md, "Review capacity is a budget".

## One writer per worktree

- **A dispatched agent owns its worktree until it reports.** The controller is just another writer:
  if it needs a change meanwhile, it waits or cuts a second worktree and merges.
- **Reviewers get their own throwaway worktree.** A reviewer's probe once leaked a deliberate
  falsification into a build tree.
- **Stage selectively.** `git add -A` in a shared tree sweeps up someone else's half-finished edit.
- **Restore state with git, not `rm`.** `git worktree remove`, `git checkout --`, `git restore`.

## Supervising lanes

The controller supervises every dispatched agent; a lane left alone can stall silently.

- **Brief short foreground steps.** Builders run each command in the foreground and see it finish;
  only the full suite named in the brief may run in the background, and no ad hoc `nohup … &` or
  detached job. *Why:* two builders stalled just before a backgrounded long step and then answered
  no status message. *Test:* the brief names the one command allowed in the background.
- **Watch the work, not the chat.** Read file modification times in the worktree, the agent's
  processes and its commits, on a cheap tick (model-routing-and-cost.md, "Recurring ticks").
- **Thresholds, stated in the brief.** About 30 minutes with no file change and no commit: one
  status ping. About 45 minutes, or no answer to the ping: stop the agent, write its uncommitted changes to a patch file (`git -C <worktree> diff > <lane>-<time>.patch`, plus `git status` for new
  files), and dispatch a fresh agent into the same worktree with the patch, the brief and the last
  completed step. Do not wait longer or ping again. *Why:* a stalled agent does not recover, and
  waiting costs the lane the time it was meant to save. *Test:* each stall in the record shows the
  ping time, the stop time, the patch path and the new agent's model.
- **Every agent reports the model identifier its runtime gave it** (model-routing-and-cost.md, rule 4). When
  notes disagree about which model held a role, that report settles it, never a pick between notes.
