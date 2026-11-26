---
name: engineering-method
description: Engineering judgement for work with a coding agent, scaled by stakes (prototype, internal tool, live system). Use it BEFORE answering even when it looks simple, whenever the user asks whether something works, passed, is deployed, live or merged, or found zero results; asks for a status update or a report of a test run; asks for steps to deploy, pull, restart or migrate a system real people use; asks which model should implement or review, or how to brief a subagent; has just declined a permission; or asks to add, change, plan, build, review or ship code of any size, even a terse one-line request or a quick script where it says to keep process light. It carries the checks a quick answer skips - evidence shown, state measured now, proven zeros, piped exit codes, in-flight work, verified backup, rollback and read-backs before a live change, a cross-model reviewer that runs probes.
when_to_use: Phrases like "is it live / deployed?", "can I tell the team", "write the status", "the tests printed", "it returned 0", "give me the steps to deploy / restart", "production", "which model should review", "review brief", "subagent", "I declined", "quick / throwaway script", "plan", "build", "ship", "merge", "is this over-engineered", "record this decision", "is this a regression", "why did it fail / refuse?", "root cause", "promote", "release", "show progress", "which step is next" on a step list, "eval plan", "setup notes", "the owner update", "personal data in a commit", "pre-push guard", "we decided this before", "just add X".
---

# engineering-method

A method for building with coding agents: each rule, its *Why:*, its *Test:*.

**These are defaults, not a cage.** Propose a better approach when you see one, and what it replaces. **Read the intent and deliver all of it:** the working thing as asked, complete, saying what
was left out and why. State assumptions and proceed; ask only what blocks the next step. Push back
once, briefly, then do it as asked unless it is unsafe (principle 13); the asked-for behaviour is
what ships. Recommend one approach and deliver it; alternatives get a sentence each, never a second
full version for the person to choose from. *Why:* literal readings and question-only replies
delivered less than the intent. *Test:* the thing as asked, its assumptions, one pushback, one pick.

**Superpowers does the procedure** (section 3, plus `brainstorming`, `subagent-driven-development`,
`using-git-worktrees`); this skill adds what it does not say, and names any
disagreement.

## 1. Decide the stakes first

The process scales with what a mistake costs. Name the tier at the start (after the update, in an update for someone else); ceremony the tier does not
need is itself a defect (principle 7). **Tier a answers look light:** the thing asked for, plus one
quick check the person can run. No process sections, no plan, no review pipeline.

| Tier | Typical work | What applies |
|---|---|---|
| **a. Exploration** | prototype, spike, notebook, throwaway script | Principles 1–4 (evidence, state claims, vendor docs, proven zeros). One review before anyone relies on it. No deploy file, no numbered docs, no ladder unless asked. |
| **b. Internal** | internal tool, take-home, single-user app, library | Tier a, plus: TDD on logic; every failure becomes a test; reviewer is a different model and executes (references/review-loop.md); a short decision note for anything non-obvious; a plan document only when the work spans sessions; a header on code the task touches (references/docs-and-decisions.md). |
| **c. Live** | a system real people use today | Everything: plan reviewed against the running code before building; per-task cross-model review plus a whole-branch pass; a deploy file from a template with a guard test; in-flight check, verified backup, read-backs, rollback, record (references/live-system-changes.md). |

Unsure between two tiers? Take the higher one for anything that writes data, sends messages, spends
money or touches credentials; the lower one otherwise.

## 2. Principles

**Truth**
1. **Evidence before assertion.** Show the command and its output, not the conclusion. *Why:* "it
   passes" has been wrong often enough to be worth nothing. *Test:* the reader can see the run, and
   a piped test run kept its exit code (`set -o pipefail`, or gate on the `OK` line).
2. **A state claim is a measurement.** "Deployed", "merged", "parked", "live", "pre-existing",
   "unchanged since" are read in the same pass, command shown, never recalled. *Why:* recalled state
   in the tone of observed state is how a fix gets believed live when it is not. *Test:* each such
   word sits next to its command; "X is live" means the running revision descends from X
   (`git merge-base --is-ancestor X <running>`), else unverified.
3. **Vendor docs before vendor claims.** Read the tool's official docs and changelog in the same pass
   and cite the page. *Why:* a field read from the system confirms or contradicts the docs; it never
   replaces them. *Test:* every vendor behaviour has a citation or is labelled a hypothesis.
4. **The global measurement rules apply** (proven zeros, fail loudly, dates read in the same pass).
   This skill adds exit codes, suite and skip counts, counts read entry by entry, negatives with their
   window, clock-only times, state words and labels (references/measurement-and-state-claims.md).

**Design**
5. **Recommend the industry practice first, then adapt.** Name the standard way and who does it,
   then say how and why this project departs. *Why:* departures should be chosen, not stumbled into.
   *Test:* every process or design recommendation names its baseline.
6. **Extend before adding.** Inventory what exists; extend it; a new tool, check or module must show
   why nothing existing can carry the job; one shared check at every exit. *Why:* duplicates drift
   and only one gets fixed. *Test:* the plan marks each capability EXTENDS or NEW.
7. **No over-engineering, in either direction; enforce what matters.** Build only when a real
   incident or measured gap is behind it, nothing already solves it (read the platform's docs), and
   it is symmetric (it does not bind the trusted while sparing the untrusted). A switch nobody should
   flip, or a guard that stops the system doing its job, is over-engineering too. A written rule that
   has been missed moves into a hook, gate, CI check or test that fails; a prose line may go with
   it, never instead. *Why:* rules kept only in prose were skipped; gated ones held. *Test:* the
   three answers are written before building; a missed rule names its check. **Code headers (tier
   b/c)** are such a rule: what the diff adds or edits carries six labelled fields (`What:` `Use when:`
   `Inputs:` `Output:` `Side effects:` `Role:`, "none" allowed), untouched code none, and a check
   enforces it (docs-and-decisions.md).
8. **A red gate is evidence against the design.** A control that leaves your own gate permanently
   red, or guards only against people who already hold everything, is a design defect to challenge,
   not a consequence to park. *Test:* no gate is red "by design" between releases.
9. **Every failure becomes a test, before the fix.** *Why:* a fix with no failing case first cannot
   show it fixed anything. *Test:* the test was red on the old code and is green on the new.

**Agents and review**
10. **Reviewer ≠ implementer, at least as strong, and it executes.** Different model family where
    possible; the reviewer writes and runs probes; an unreproduced finding is a hypothesis. *Why:*
    same-model review grades its own homework. *Test:* each finding names its probe (review-loop.md).
11. **Route models by what a mistake costs and whether a test would catch it.** Turn count beats token
    price; brief, never corpus; bounds enforced; name the model on every dispatch, and each agent
    reports the model it ran as; recurring ticks run on a cheap agent. *Test:* model-routing-and-cost.md.
12. **One writer per worktree; parallel only when regions differ and neither needs the other's
    output. A blocked release goes first and alone; work in progress is capped by reviewer capacity**
    (Kanban WIP limits, Theory of Constraints). *Why:* new lanes starve the reviewer a held release
    needs. *Test:* references/parallel-and-worktrees.md.

**Live systems and permission**
13. **Read-only by default on anything real people use; ask before mutating.** Steps for a live change
    fill every REQUIRED slot with this system's actual command or condition, never a restatement:
    **Proven off live** (suite or CI green on the exact revision, or a staging run; never tests inside
    live). **Rollback point** (running revision saved). **What ships** (log and diff of the incoming
    change; data, schema or config it touches backed up and the backup read back, or "code-only,
    checked"). **Rollback** (commands that return to the saved revision and restore any backup, plus a concrete
    trigger, ready before starting). **Settings and data** (each new setting set to a stated value;
    data under a changed key or format handled, the choice written). **In-flight** (a command, the last
    step before the switch). **Read-backs** (running revision, health, one real use). No test traffic
    to an instance users are about to meet. *Test:* references/live-system-changes.md.
14. **A declined permission means stop.** No retry, narrower form or move to a path that does not
    prompt; mark it unverified. *Why:* a workaround defeats the decision. *Test:* the report lists it.

**Record and report**
15. **Record as you go, not after.** Decisions append to a log, never rewritten; new documents are
    indexed the same day. The plan's stage and a configured tracker move at each stage change, pause, handoff and
    release, reconciled on events by plan-layer's controller (`move.py`, `sync --tracker`;
    `/plan-layer pause` before stopping; it owns how, this skill when). *Why:* the next session re-derives what this one did not write. *Test:* the report says when.
16. **Plain words, exact terms, progress as a ladder.** Short sentences; the real technical name,
    defined once; words whose plain meaning matches ("tested on the bench", never "benched", which
    reads as sidelined); on tier c (or when asked) the ladder or release tree, measured, with a caveat
    line and the promotion grid; one naming hierarchy (E-01.S2, R-04, D-001). An update for
    someone not in the session: the reply's first line is `**Needs you**` (no tier, note or preface
    above it); each decision with options, deadline, why it matters; each item with plain meaning,
    `since <last update's time>:` and its source in brackets; every id glossed in every section;
    notes to the asker last. *Test:* progress-ladder.md.

**Delivery (tier c; tier b where it applies)**
17. **Root cause, not symptom; the fix fits what exists.** Replay the case first (root-cause-investigation.md);
    the cause is a hypothesis until measured. A fix plan then has a "Fit with what exists" section
    with four REQUIRED lines: **Exists:** every mechanism already on the concept, absent ones named
    absent. **Extends:** the smallest one, where the property must hold (no mechanism beside it).
    **Unlocks:** what it makes possible beyond this case (a change that covers only this case, proposed or yours, is named a patch). **Goals:**
    one line per stated goal, met and how. A repeat fault changes the mechanism. *Why:* symptom
    fixes came back. *Test:* the four lines are there.
18. **No regression is a hard gate.** Settle "is this a regression?" by the same check on what
    production runs; an unexplained base-vs-head difference stops the release. *Test:* both runs shown.
19. **Rehearse the procedure, test once, promote the artifact.** Dry-run the deploy file on a
    production-shaped bench; a real-model bench precedes production; the tested digest ships. *Why:*
    faked-model goldens miss timing and retries. *Test:* references/live-system-changes.md.
20. **The record is searched and re-tested before it is cited, and guarded before it leaves.** *Why:*
    a missed ruling gets re-argued, and a pushed secret cannot be taken back. *Test:*
    references/docs-and-decisions.md ("Using the record"), live-system-changes.md ("Pushing").
21. **Under a standing go, decide engineering calls and keep moving; ask only true owner gates.**
    Sort each question: mine (decide, log the reason), the owner's later (park with a trigger), the
    owner's now (spend, credentials, irreversible sends, scope). Never idle or defer on your own.
    *Why:* asking what you could decide stalls the work. *Test:* review-loop.md ("Autonomy").
22. **Agentic products: code holds the safety floor; meaning goes to the model.** Code enforces only
    provenance, authority, what leaves unconfirmed (irreversible actions, sends), secrets and spend;
    meaning is a tool or fact for the model (one tool per action, a lookup, clear descriptions), which
    asks when unsure (the guardrails pattern). *Why:* keyword branches for meaning grew a brittle adapter that missed the
    next phrasing. *Test:* every rule in code is on the floor list.

## 3. The stage map

**At each stage change, re-read that stage's row and load its skill and references; after
compaction or `/clear`, re-load this whole skill.** The plugin's hooks remind you; if they did not
fire, do it anyway. A stage needs no trigger word: handing finished work to users is a release.

| Stage | Skill | References | What this method adds |
|---|---|---|---|
| plan | `superpowers:writing-plans` | docs-and-decisions.md, parallel-and-worktrees.md | out-of-scope list; EXTENDS/NEW per capability; a fix plan follows principle 17; tier c: a fresh reviewer reads it against the running code |
| debug | `superpowers:systematic-debugging` | root-cause-investigation.md, measurement-and-state-claims.md | steps RC-1 to RC-10 by name; decided, told and judged kept apart |
| build | `superpowers:test-driven-development` | model-routing-and-cost.md, parallel-and-worktrees.md | principle 9; tier b/c: headers on touched code, with their check (docs-and-decisions.md); the full suite once before reporting; a held release first |
| review | `superpowers:requesting-code-review` | review-loop.md | a different model that runs probes; usage read before launching; re-reviews cover the delta; nothing competes with a held release |
| test | `superpowers:verification-before-completion` | measurement-and-state-claims.md, behaviour-evals.md | principles 1, 2, 4; counts entry by entry; plan: run scripts/plan_conformance.py <file>; owner rules mismatches; evals: cost cap, layered, isolated, fail-closed sends |
| deploy | (none) | live-system-changes.md | principle 13; what the diff does not show, handled first; pre-launch instances get no test traffic; helper faults split read-only from state-changing |
| merge | `superpowers:finishing-a-development-branch` | live-system-changes.md | the push guard covers every party's identifiers and every git dir pushed from |
| release | (none) | live-system-changes.md, progress-ladder.md | a summary is not proof: full suite on the current head and a different-model review, then the deploy row |
| report | (none) | progress-ladder.md, measurement-and-state-claims.md | "needs you" first, every id glossed and sourced; the release tree; a step list in progress is reprinted whole with its ticks |

## 4. References (load at their stage, or when the task needs them)

`references/`: `review-loop.md` (reviewer, probes, fix rounds, briefs, autonomy),
`model-routing-and-cost.md` (models, capacity, cheap ticks), `measurement-and-state-claims.md` (exit
codes, skips, counts, negatives, state words), `progress-ladder.md` (ladder, release tree, grid,
updates, checklists), `parallel-and-worktrees.md` (fan-out, writers, lanes),
`live-system-changes.md` (deploy standard and file, proving a release, pre-launch, pushing),
`docs-and-decisions.md` (docs, headers, decision log, the record, names),
`behaviour-evals.md` (evals as a dataset, cost cap, contamination, baselines),
`root-cause-investigation.md` (RC-1 to RC-10), `permission-profiles.md` (settings per tier).
