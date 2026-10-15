# Model routing and cost

## The one question

Not "how hard is the task" but **"what does a mistake cost here, and would a test catch it?"**

| Tier | Use for |
|---|---|
| **Strongest** | anything needing a sweep or judgement (find every call site, extend a mechanism across paths); every review that must break something; whole-branch reviews; plans that shape a security decision; research that shapes a decision; fix-loop escalation (see below) |
| **Mid** | the floor for reviewers and for any implementer working from prose rather than code; multi-file integration; task-level review of a small diff |
| **Cheapest** | transcription where the plan carries the complete code; single-file mechanical fixes; log filtering, grep and summarise, formatting — nothing a person acts on unchecked |

This matches `superpowers:subagent-driven-development` (its model-selection section); it is restated
here only to add the question above and the rules below.

A history of failed sweeps (one rule needing to hold in six places, found one place per pass) is
exactly where the stronger model pays for itself.

## Rules that override the table

1. **Turn count beats token price.** A cheap model that takes three times the turns costs more and
   pollutes context. Mid tier is the floor for any worker working from prose rather than code.
2. **Escalate on failure** by Superpowers' fix rounds (`subagent-driven-development`): early rounds
   resume the implementer; later rounds go to a fresh implementer at least one tier up.
3. **The model does not fix independence.** See `review-loop.md`.
4. **Name the model on every dispatch.** An omitted model inherits the session's and silently
   defeats the routing.
5. **Not the strongest model for long planning documents.** Length, not model strength, is the cost
   there; one measurement found three times the tokens spent drafting plans as on the code they
   described.

## Keeping agents cheap

An agent costs **its context size times its turn count**. So does the controlling session, on
every request.

- **Brief, never corpus.** Extract the fifty relevant lines; do not hand an agent whole files.
- **Implementers run the suite once before committing and never loop on a long run; the controller
  runs it on the merged head.** Implementers that re-ran long suites stalled without committing,
  repeatedly.
- **Bounds are enforced, not stated.** Give a tool-call bound; an agent past it is told "stop and
  report", not left to finish. Unenforced bounds were overrun three-fold in practice.
- **Compact or start fresh before a long mechanical phase** (a deploy, a suite run, a sweep). The
  plan, the ledger and the deploy file carry the state.
- **Defer work that waits on something anyway.** Building early against a moving head costs
  everything and gains nothing.
- **Lanes only when speed is asked for and the regions are disjoint.** Four lanes with four reviews
  is the expensive shape; one or two is the default.
- **Before choosing a weaker model to save usage, read the current limits (/usage); never recall
  them.** The usual cost driver is context length × turns, so save by fresh sessions and tight
  briefs before downgrading models.
- **An eval that decides whether something ships runs on the model that will use it, graded by a
  mid-tier-or-better judge.**
