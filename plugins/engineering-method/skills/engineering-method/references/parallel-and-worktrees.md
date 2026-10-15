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

Parallel is not free: each lane carries a review. Fan out when speed is asked for and the test
passes, not by reflex.

## One writer per worktree

- **A dispatched agent owns its worktree until it reports.** The controller is just another writer:
  if it needs a change meanwhile, it waits or cuts a second worktree and merges.
- **Reviewers get their own throwaway worktree.** A reviewer's probe once leaked a deliberate
  falsification into a build tree.
- **Stage selectively.** `git add -A` in a shared tree sweeps up someone else's half-finished edit.
- **Restore state with git, not `rm`.** `git worktree remove`, `git checkout --`, `git restore`.
