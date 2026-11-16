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
4. **Name the model on every dispatch, and have every agent report the model id it actually ran
   as.** An omitted model inherits the session's and silently defeats the routing. The report's
   first line carries the model id the agent read from its own runtime; the ledger records that, not
   the brief's intent. *Why:* role assignments flipped between notes, and the model that actually ran
   could not be shown. *Test:* every ledger row names the reported model id, and a disagreement
   between notes is settled from that report.
5. **Not the strongest model for long planning documents.** Length, not model strength, is the cost
   there; one measurement found three times the tokens spent drafting plans as on the code they
   described.

## Keeping agents cheap

An agent costs **its context size times its turn count**. So does the controlling session, on
every request.

- **Brief, never corpus.** Extract the fifty relevant lines; do not hand an agent whole files.
- **Builders run the full suite once before reporting and never loop on a long run; the controller
  runs it again on the merged head, inside the project tree.** Implementers that re-ran long suites
  stalled without committing, repeatedly; runs of touched modules only missed failures elsewhere
  (measurement-and-state-claims.md, "Suite results").
- **Bounds are enforced, not stated.** Give a tool-call bound; an agent past it is told "stop and
  report", not left to finish. Unenforced bounds were overrun three-fold in practice.
- **Compact or start fresh before a long mechanical phase** (a deploy, a suite run, a sweep). The
  plan, the ledger and the deploy file carry the state.
- **Defer work that waits on something anyway.** Building early against a moving head costs
  everything and gains nothing.
- **Lanes when the parallel test passes, sized to what can be reviewed.** Four lanes with four
  reviews is the expensive shape; two or three is the usual size (parallel-and-worktrees.md).
- **Before choosing a weaker model to save usage, read the current limits (/usage); never recall
  them.** The usual cost driver is context length × turns, so save by fresh sessions and tight
  briefs before downgrading models.
- **Recurring ticks run on a cheap agent, never in the main session.** A status check, poll or
  `/loop` that repeats (every 15 minutes, every hour) goes to a cheapest-tier agent or a small script
  plus a cheap model: it reads the state (worktree file times, processes, commits, logs) and writes a
  short report to a file; the main strong-model session reads only that report, and only when it
  flags something. *Why:* each tick in the main session re-sends its whole context; one 15-minute tick
  cost about a million tokens a run across dozens of runs. *Test:* no recurring job is scheduled in
  the controlling session; the report file names the agent's model.

## Review capacity is a budget

The strongest reviewer's usage limit is the scarcest resource on most days (FinOps and capacity
planning: measure the budget, then allocate it to the highest-value work first).

- **Read the usage readout before launching any review**, and size the day's reviews to it: cite
  the figure and its reset time, estimate a review's cost (or measure the first one by reading usage
  before and after), and order the reviews so the held release's fits first. *Why:* the reviewer's
  weekly limit ran out in the middle of a release. *Test:* the plan quotes the readout with its read
  time, and the reviews it launches fit inside it.
- **Re-reviews cover only the delta** (the fix commit's diff and what it touches), never the whole
  branch again (review-loop.md, "Fix rounds"). *Test:* the re-review brief names the fix commit.
- **No whole-branch review while a release is held**; the capacity goes to unblocking it
  (parallel-and-worktrees.md, "Bottleneck first").
- **Do not drop below the reviewer floor to make reviews fit.** Defer them to the reset instead;
  the defer is stated with the date.
- **An eval that decides whether something ships runs on the model that will use it, graded by a
  mid-tier-or-better judge.**
