---
name: engineering-method
description: Engineering judgement for work with a coding agent, scaled by stakes (prototype, internal tool, live system). Use it BEFORE answering, even when the question looks simple, whenever the user asks whether something works, passed, is deployed, live or merged, or found zero results; asks for a status update or a report of a test run; asks for steps to deploy, pull, restart or migrate a system real people use; asks which model should implement or review, or how to brief a subagent; has just declined a permission; or is planning, building, reviewing or shipping code of any size, including a quick script, where it says to keep process light. It carries the checks a quick answer skips - evidence shown, state measured now, zeros proven able to be non-zero, piped exit codes, in-flight work, verified backup, rollback and read-backs before a live change, a cross-model reviewer that runs probes.
when_to_use: Phrases like "is it live / deployed?", "can I tell the team", "write the status", "the tests printed", "it returned 0", "give me the steps to deploy / restart", "production", "which model should review", "review brief", "subagent", "I declined", "quick / throwaway script", "plan", "build", "ship", "merge", "is this over-engineered", "record this decision".
---

# engineering-method

A method for building with coding agents, learnt the expensive way. Each principle is a rule, the
reason in one line, and a test for whether it held.

**These are defaults, not a cage.** When you see a better approach for the task in front of you,
propose it, say what it replaces and why, and use it once agreed. Producing something better than
asked is the point; following this file to the letter while doing worse is not.

**Superpowers does the procedure.** This skill does not restate brainstorming, plans, TDD, code
review, debugging, worktrees or verification. It points to those skills (table below) and adds only
what they do not say. If this file and a Superpowers skill seem to disagree, say so rather than
silently picking one.

## 1. Decide the stakes first

The process scales with what a mistake costs. Name the tier at the start; ceremony the tier does not
need is itself a defect (principle 7). **Tier a answers look light:** the thing asked for, plus one
quick check the person can run. No process sections, no plan, no review pipeline.

| Tier | Typical work | What applies |
|---|---|---|
| **a. Exploration** | prototype, spike, notebook, throwaway script | Principles 1–4 (evidence, state claims, vendor docs, proven zeros). One review before anyone relies on it. No deploy file, no numbered docs, no ladder unless asked. |
| **b. Internal** | internal tool, take-home, single-user app, library | Tier a, plus: TDD on logic; every failure becomes a test; reviewer is a different model and executes (references/review-loop.md); a short decision note for anything non-obvious; a plan document only when the work spans sessions. |
| **c. Live** | a system real people use today | Everything: plan reviewed against the running code before building; per-task cross-model review plus a whole-branch pass; a deploy file from a template with a guard test; in-flight check, verified backup, read-backs, rollback, record (references/live-system-changes.md). |

Unsure between two tiers? Take the higher one for anything that writes data, sends messages, spends
money or touches credentials; the lower one otherwise.

## 2. Principles

**Truth**
1. **Evidence before assertion.** Show the command and its output, not the conclusion. *Why:* a
   claim that "it passes" has been wrong often enough to be worth nothing. *Test:* the reader can see
   the run, and a piped test run kept its exit code (`set -o pipefail`, or gate on the `OK` line).
2. **A state claim is a measurement.** "Deployed", "merged", "parked", "live", "pre-existing",
   "unchanged since" are read in the same pass, command shown, never recalled. *Why:* recalled state
   in the tone of observed state is how a fix gets believed live when it is not. *Test:* each such
   word sits next to the command that proved it (references/measurement-and-state-claims.md). For
   "commit X is live": read the revision the running system reports, then check it is or descends
   from X (`git merge-base --is-ancestor X <running>`); until then the status line says unverified.
3. **Vendor docs before vendor claims.** Read the tool's official docs and changelog in the same pass
   and cite the page before designing around its behaviour. *Why:* a field read from the system
   confirms or contradicts the docs; it never replaces them. *Test:* every vendor behaviour has a
   citation or is labelled a hypothesis.
4. **The global measurement rules apply** (proven zeros, fail loudly, dates read in the same pass).
   This skill adds exit codes, state words and labels (references/measurement-and-state-claims.md).

**Design**
5. **Recommend the industry practice first, then adapt.** Name the standard way and who does it,
   then say how and why this project departs. *Why:* departures should be chosen, not stumbled into.
   *Test:* every process or design recommendation names its baseline.
6. **Extend before adding.** Inventory what exists; extend it; a new tool, check or module must show
   why nothing existing can carry the job. One shared check reused at every exit, never one per exit.
   *Why:* duplicates drift and only one of them gets fixed. *Test:* the plan marks each capability
   EXTENDS or NEW with a reason.
7. **No over-engineering, in either direction.** Build only when all three hold: a real incident or
   measured gap is behind it; nothing already solves it (read the platform's docs first); it is
   symmetric (it does not bind the trusted while sparing the untrusted). A switch nobody should flip
   is over-engineering with extra steps: delete it or ship it on. A guard that stops the system doing
   its job is over-engineering too. *Test:* the three answers are written down before building.
8. **A red gate is evidence against the design.** A control that leaves your own gate permanently
   red, or guards only against people who already hold everything, is a design defect to challenge,
   not a consequence to park. *Test:* no gate is red "by design" between releases.
9. **Every failure becomes a test, before the fix.** *Why:* a fix with no failing case first cannot
   show it fixed anything. *Test:* the test was red on the old code and is green on the new.

**Agents and review**
10. **Reviewer ≠ implementer, at least as strong, and it executes.** Different model family where
    possible; the reviewer writes and runs probes; an unreproduced finding is a hypothesis.
    *Why:* same-model review grades its own homework, and reading the diff misses what running it
    finds. *Test:* each finding names the probe that reproduced it (references/review-loop.md).
11. **Route models by what a mistake costs and whether a test would catch it.** Not by how hard the
    task feels. Turn count beats token price; brief, never corpus; bounds enforced, not stated.
    Always name the model when dispatching. *Test:* references/model-routing-and-cost.md.
12. **One writer per worktree; parallel only when regions differ and neither needs the other's
    output.** *Why:* two writers interleave commits; dependent lanes produce "my sibling moved"
    defects. *Test:* references/parallel-and-worktrees.md.

**Live systems and permission**
13. **Read-only by default on anything real people use.** Ask before mutating; never restart blind
    (check in-flight work first, and again right before switching); back up and read the backup back
    before change; write the rollback commands and the trigger that fires them BEFORE the change;
    after it, read back the running revision and a real health path; prove on a copy before
    production; never run test suites inside the live system. *Test:*
    references/live-system-changes.md.
14. **A declined permission means stop.** No retry, no narrower form, no moving the same action to a
    path that does not prompt. Say plainly that it was declined, mark the check unverified and report. *Why:* a workaround defeats the
    decision the person just made. *Test:* the report lists what was declined and left unverified.

**Record and report**
15. **Record as you go, not after.** Decisions append to a log, never rewritten; new documents are
    indexed the same day; the plan's stage moves when the work moves. *Why:* the next session
    re-derives whatever this one did not write down. *Test:* references/docs-and-decisions.md.
16. **Plain words, exact terms, progress as a ladder.** Short sentences; keep the real technical name
    and define it once; on tier c (or when asked) report progress as the ladder with measured numbers. *Test:*
    references/progress-ladder.md.

## 3. Which Superpowers skill, when

| Moment | Skill | What this method adds |
|---|---|---|
| Intent is fuzzy | `superpowers:brainstorming` | name the stakes tier; principle 5 |
| Writing the plan | `superpowers:writing-plans` | an out-of-scope list; EXTENDS/NEW per capability; tier c: a fresh reviewer reads it against the running code before building |
| Building | `superpowers:test-driven-development` | principle 9; implementers run the suite once before committing, never loop on a long run |
| Many tasks in one session | `superpowers:subagent-driven-development` | principles 10–12 |
| Independent work at once | `superpowers:dispatching-parallel-agents` | the parallel test in references/parallel-and-worktrees.md |
| Isolation | `superpowers:using-git-worktrees` | one writer per worktree; reviewers get their own |
| Review | `superpowers:requesting-code-review` / `receiving-code-review` | references/review-loop.md |
| Something broke | `superpowers:systematic-debugging` | principle 8; principle 2 for every "it was already broken" |
| Before saying done | `superpowers:verification-before-completion` | principles 1, 2, 4 |
| Merging | `superpowers:finishing-a-development-branch` | tier c: references/live-system-changes.md |

## 4. References (load when the task needs them)

- `references/review-loop.md` — cross-model reviewer, probes, scoped re-review, fix-round escalation
- `references/model-routing-and-cost.md` — which model for which job, and how agents stay cheap
- `references/measurement-and-state-claims.md` — exit codes, state words, labels (adds to the global measurement rules)
- `references/progress-ladder.md` — the progress format, with a filled example
- `references/parallel-and-worktrees.md` — when to fan out, and who may write where
- `references/live-system-changes.md` — the deploy standard: template, guard test, in-flight, backup, rollback
- `references/docs-and-decisions.md` — numbered docs, headers, the decision log, the index
