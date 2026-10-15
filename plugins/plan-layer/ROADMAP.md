# plan-layer — known gaps

**Written 2026-08-10 (UTC), at v0.3.0.** Deliberately not being worked on. This file exists
so the reasoning survives the session it came from.

## Why this file exists

> **Updated 2026-08-17.** Two of these have moved since the file was written, and saying so
> matters more than keeping the list tidy.
>
> **Gap 2 is partly closed.** The agent no longer only grades itself: the gate now catches the
> page contradicting *itself* — not-yet language beside finished tasks, a capability marked
> untouched while work runs against it, a dependency pointing at something merely queued. Those
> are objective and need no reviewer. What remains open is the harder half: a claim that is
> internally consistent and simply wrong about the world. Executable assertions cover that for a
> fixed set of facts (twelve, in the project this came from), not for the whole page. **An
> independent reviewer is still the right answer for the rest.**
>
> **Gap 3 is unchanged and now the most valuable.** Every miss so far — three of them — was caught
> by the human reading the page, not by the tooling. There is still no way for them to mark a
> claim as disputed and have the gate hold it open.
>
> **Gap 1 and Gap 4 are unchanged.**



plan-layer was built to solve one problem: **a coding agent's memory ends with its context
window, and a human's memory of what the agent did ends sooner.** State lives in a file both
sides read, and the reading is automatic.

Against the 2026 consensus for agent-assisted development — durable state outside the context
window, a machine-readable spec both sides edit, verification gates — this clears the bar,
and the executable assertions in 0.3.0 go past it. Most "living documentation" is prose that
rots; this fails a gate when it drifts.

Three things it still does not do. None is a defect; each is a real limit, and knowing which
is which is the point of writing them down.

---

## Gap 1 — no history

> **Partly closed, 0.14.0 (27 Sep 2026).** History is now KEPT: `roll.py` moves aged records into
> `plan/archive/*.json` in full and the page counts them. It is not yet READABLE from the page —
> there is no view over the archive and no record of transitions (when an invariant broke). An
> archive index is queued on the plugin's own plan; transitions remain open as written below.
>
> **Size, partly closed, 0.16.0 (15 Oct 2026).** Kept history only helped if someone ran `roll.py`,
> and on a two-month project nobody did: `plan.json` reached 212 KB. `sync.py` now rolls on every run
> (212 → 172 KB measured on a copy) and the budget is `meta.size_budget_kb`. Still open, honestly:
> rolling moves only history (done, changelog, the queue's tail). Live state — parked questions,
> edge cases, capabilities, a finished item's long checklist — is not rolled and can still grow past
> the budget; on that project those four held about 97 KB of the 172 KB after the roll. There is no pruning
> feature; the gate's DRIFT is the only signal.


`plan.json` is a **snapshot**. It says an invariant is at risk; it cannot say *when it broke*
or *what changed the day it did*. Answering that means reading git log by hand, which is
exactly the manual archaeology this tool exists to remove.

**What done looks like:** the page can answer "when did this change, and what else moved at
the same time?" without leaving it.

**Sketch.** A `plan/history.jsonl` — one append-only line per transition: timestamp, what
changed (`invariants.backup: holding → at risk`, `plans.now[0].stage: grounded → planned`),
and the commit it happened in. `render.py` computes the diff against the previous state on
each render and appends; the page renders a compact timeline per invariant and per active
item. Append-only, so it is cheap and cannot be rewritten into a flattering shape.

**Why it is not urgent:** git already holds this, just inconveniently. The cost is minutes of
archaeology a few times a month, not a wrong decision.

**Effort:** small. Half a day, mostly deciding what counts as a transition worth recording.

---

## Gap 2 — the agent grades its own homework

This is the real one.

Today the agent writes the plan, writes the evidence for the plan, and mostly runs the gate
on the plan. The gate catches *structural* dishonesty — progress claimed without evidence, a
dangling reference, an alarm with no detail. It cannot catch **an agent that is confidently
wrong in a well-formed way**, which is the failure mode that actually happens.

The evidence that this is real, from one evening on 2026-08-09:

- The plan claimed **14,051 transcripts**; the archive holds **7,069**. Well-formed, passed
  every check, wrong for weeks.
- Production's agent count was wrong. Staging's was wrong.
- **Tracing was missing from the one system that had it**, while both systems without it
  described it.

Every one of those was found by a human reading the page, not by the tool.

**What done looks like:** something other than the author checks the work, before the human
has to.

**Sketch.** A reviewer subagent with a deliberately narrow remit: **read the plan and the
repository, report disagreements, never edit anything.** Read-only tools only — the value
comes from it having no stake in the plan being right. It runs on demand
(`/plan-layer audit`) and reports: claims the repository contradicts, capabilities whose
evidence is stale relative to the files they describe, items whose stage does not match what
the working tree shows.

**Open packaging question:** ship it inside plan-layer (it needs the schema) or as a sibling
plugin in this marketplace (it is a different job)? Leaning inside plan-layer — it is
worthless without the plan format, and a plugin that cannot work alone should not pretend to.

**Prerequisite already met:** the founder authorized subagent-driven development for this
workstream on 2026-07-28. It has never been used this way.

**Effort:** medium. The agent definition is small; deciding what it is allowed to conclude,
and how it reports without becoming noise, is the work.

---

## Gap 3 — one-directional

The artifact tells the human what the agent did. There is no path for the human to *inject* a
correction except by telling the agent in conversation.

On 2026-08-09 the founder corrected the artifact four separate times — a missing capability, a
figure/table mismatch, absent tracing, drifted facts. **Each time, following the thread found
more than had been flagged.** That is a signal, not a compliment: **the human is currently
the drift detector**, and a detector that only fires when someone happens to read carefully is
not a control.

**What done looks like:** the human can mark a claim as disputed in a way the tool respects,
without needing the agent present or cooperative.

**Sketch.** The lightest thing that works: a `disputed` flag any human can add by hand to a
fact, a capability, or an item — `"disputed": "the corpus number looks wrong to me"`. The
renderer marks it visibly; the gate **fails** while anything is disputed. It costs the human
one line of JSON and cannot be argued away by the agent, which is the point. Resolving it
requires evidence, not agreement.

Note the relationship to Gap 2: an independent auditor reduces how often the human has to
dispute anything, but does not remove the need for the channel.

**Effort:** small. The discipline is harder than the code — the agent must never clear a
`disputed` flag on its own.

---

## Gap 4 — the plugin does not use itself

> **Closed, 0.14.0 (27 Sep 2026).** `plan/plan.json` at the root of this repository is the plugin's
> own plan, rendered and gated by its own scripts. The three open gaps above are its queued items.


`ai-engineering-sdlc-tools` has no `plan/plan.json` of its own. A planning tool that does not
plan with itself has not met its own users. Doing so would have surfaced Gaps 1–3 sooner, and
would make this file redundant — these would simply be items on the plugin's own page.

**Effort:** trivial. Deliberately deferred with the rest, so the ordering below stays honest.

---

## Ordering, and why: do none of this now

**Recommendation on 2026-08-10: none of the four.**

The planning layer is already better than the tooling most teams run. **The product has not
moved since 2026-08-06.** The gap that costs money is the email and redaction layer sitting
unsupervised in a `tmux` session on a production box, absent from the file backup — not the
planning layer's missing history view.

Building tooling is more comfortable than building the thing the tooling is about. That is
precisely why this is written down rather than acted on.

**Revisit trigger:** after the email capture plan lands and is executed.

**Then take Gap 2 first.** It is the one that stops the human being the drift detector, and
the other three are conveniences by comparison. Gap 4 is a good warm-up for it — the auditor
needs a plan to audit, and the plugin's own would be an honest first target.
