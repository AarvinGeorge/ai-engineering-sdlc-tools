# The review loop

Superpowers' `requesting-code-review` and `receiving-code-review` say how to ask for and take a
review. This file says who reviews, what they must do, and when to stop.

## Who reviews

- **Never the implementer's model.** A model scores its own output above an equally good one from
  elsewhere (self-preference bias in LLM-as-judge is well documented, alongside position and
  verbosity bias). Same-model review weakens the gate at no saving.
- **At least as strong as the implementer.** Strong implements, the other strong reviews; a
  mid-tier implementer can be reviewed by either strong model. A ranking between two models is a
  vendor claim: cite it, or say it is unverified and how the person can check it.
- **A fresh agent per task.** Fresh context, a brief and a diff, never the implementer's
  conversation.
- **A final whole-branch pass** on tier c work, from a different angle than the per-task reviews.
  If the same model that implemented does this pass, say so: the per-task cross-model reviews are
  then the independence check, and the final pass is a second read, not the only one.

## What a reviewer must do

- **Execute, not reason from the diff.** Write focused, bounded probes and run them — never the
  package-wide suite. This adds to the Superpowers reviewer prompt; it does not replace it. On the project this came
  from, every Critical found across five rounds came from a reviewer that ran probes; none from one
  that read carefully. An unreproduced finding is labelled a hypothesis.
- **Start from what worked yesterday.** Ask first what this change could break that was working;
  then the risks the change's own shape creates (a guard added for three verbs that a fourth walks
  around; a function deleted while another path still calls it). A generic checklist finds less.
- **File and line for every verdict.** The reviewer is itself wrong roughly once per round; the code
  settles it, so a fix round re-reads every cited line instead of trusting the finding.
- **Its own worktree.** A reviewer's probe that edits files must never land in a build tree.
- **Plans too.** On tier c, a written plan is reviewed against the running code before anything is
  built. Self-review of a plan passed two plans that three review rounds then found five Criticals in.
- **Every stage carries its review, run as part of the stage.** On tier c, plan, task, branch, bench
  and promotion each get theirs in the same step (tier b: plan and task); never end a stage by asking whether to review. Only
  the go or no-go word is asked of the person. *Why:* a review listed as "next" is a review that
  waits on a reminder. *Test:* the plan's task list has a review row for every stage.

## Fix rounds

- **One review per task. A scoped re-review only for a Critical, an Important on a security
  boundary, or code the reviewer wrote (below).** Test-only and docs-only fixes are read by the controller from the diff when the
  implementer's report shows red, then green. **This is a deliberate departure from Superpowers**,
  which re-reviews every fix round: it trades a small risk on low-stakes fix diffs for cost. On tier c
  work, or when unsure, follow Superpowers and re-review every round.
- **A re-review covers the delta, not the branch.** Brief it with the fix commit, its diff, the
  finding it answers and what the fix touches; a whole-branch pass is a separate, scheduled review,
  never a re-review, and never while a release is held. Read the reviewer's usage before launching
  it (model-routing-and-cost.md, "Review capacity is a budget"). *Why:* whole-branch re-reviews
  spent the reviewer's weekly limit on code already reviewed. *Test:* the re-review brief names the
  fix commit and its line count.
- **Code the reviewer wrote gets its own re-review.** When a fix is taken as code from the review
  (not as a finding the implementer then fixes), the reviewer is its author, so someone else reads
  it, whatever its severity. *Why:* a fix taken as written from a review
  slipped in a regression; the suggestion had been reviewed, the code had not. *Test:* the fix
  diff has its own review row naming a reviewer other than its author.
- **A fix that adds a check in one branch is usually the wrong shape.** Ask where the property must
  hold and put it there, once.
- **Escalate, cap, and stop on a stall** (one rule; model-routing-and-cost.md points here). A fix
  round is one fix dispatch plus its scoped re-review (or the controller's read of a test-only or
  docs-only fix, above); Z is the number of open Critical and Important findings after it.
  Baseline, Superpowers' `subagent-driven-development`: at most five rounds per task (per document,
  for a plan or deploy-file review); rounds 1-3 resume the implementer, rounds 4-5 take a fresh
  implementer on a more capable model; after round 5 the controller adjudicates each open finding
  (park it with a ruling, or BLOCKED to the owner). GSD's `gates.md` adds stall detection: escalate
  early when the issue count does not fall between iterations. **A round stalls** when a finding
  marked addressed comes back open, or when Z is above zero and not lower than after the previous
  round (the review itself, for round 1). Stalls count per task (per document, for a plan or
  deploy-file review), across rounds. Two departures from Superpowers, which adjudicates only at
  the cap, both triggered by stall detection, GSD's idea: on the first stall on the task, the next
  round goes to a fresh implementer on a more capable model (at the top tier, a fresh implementer
  on the same model), whatever the round number; on a second stall on the task, dispatching stops
  before the cap and the controller adjudicates as at the cap (park with a ruling, or BLOCKED to
  the owner). The cap is five for every review loop, plan and deploy-file reviews included, not
  GSD's three for plans: the stall rule already ends a loop that is not converging, and one number
  for every loop is one rule to check. *Why:* the escalation line said who takes each round but
  never when the rounds end, and a round that reopens what it closed spends review capacity
  without converging. *Test:* the review's ledger line states the starting Z; each round's line is
  Superpowers' (`Task N: fix round R/5 (...; commits a..b)`) carrying `closed X, reopened Y, open Z`
  (Critical and Important only), ending `stall` when the round stalls; no task shows a round after
  a second stall on it or after round 5.
- **Record a residual rather than hiding it.** A known limit, stated, is a decision; a hidden one is
  a defect waiting.

## The reviewer's brief

Brief plus diff, never a corpus. Over about 60 KB of diff, split by commit or point the reviewer at
the changed regions only. Name: the intent, the base commit, the specific risks, what must not
regress, the tool-call bound, and "if a command is declined, do not retry, narrow or relocate it;
mark it unverified".

## The executor's brief

An agent that runs a procedure (a deploy file, a bench, a migration) needs more than a reviewer:

- **Short foreground steps.** Each command runs in the foreground and is seen to finish; only the
  full suite the brief names may run in the background. The brief states the supervision thresholds
  (parallel-and-worktrees.md, "Supervising lanes") and asks for the model id in the first line of
  the report. *Why:* agents stalled behind a backgrounded long step. *Test:* the brief names the one
  background command.
- **Full output, never a tail.** It returns the complete output of each check. *Why:* a summary
  hides which line failed. *Test:* the report carries each check's output.
- **The shell, named.** Say which shell runs the commands (zsh does not split a variable into
  words; `$b:r` is a modifier there), and keep strict mode on. *Why:* the same line means different
  things in bash and zsh. *Test:* the brief names the shell.
- **A call budget sized to the procedure.** Count the steps, add margin for retries on flaky
  connections. *Why:* a budget smaller than the file stops the run in the middle. *Test:* the brief
  shows the step count beside the budget.
- **Safe stopping points, named.** Mark the steps after which it may stop and resume without
  leaving state half-changed; at the budget it stops at the last one and reports the next step.
  *Why:* executors bound too tightly stopped mid-procedure, and the next pass had to rediscover
  where. *Test:* the brief lists the stopping points; the report names the last completed step.

## Autonomy under a standing go

When the owner has given a standing go for a body of work, the agent does not stop to ask about
calls it can make itself.

- **Sort every open question into three.** *Mine:* an engineering call inside the agreed scope;
  decide it, log it with the reason, keep moving. *The owner's, later:* park it with the trigger
  that brings it back. *The owner's, now:* a true gate (money, credentials, an irreversible send
  to real people, a change of scope or of a past ruling); ask it plainly, once, and keep working on
  anything it does not block. *Why:* asking about what you could decide stalls the work and spends
  the owner's attention; deciding the owner's gate takes it from them. *Test:* each question in the
  report carries its sort, and the decision log holds the calls made.
- **Never idle or defer on your own.** Putting work off to "tomorrow" or "after the owner replies"
  needs a reason the owner gave or a real dependency. *Why:* self-imposed waits cost the owner a
  day for nothing. *Test:* every deferral names its dependency or the ruling behind it.
- **A standing go does not cover what the go excludes.** Principles 13 and 14 still hold: a
  declined permission stops, and a live mutation is announced. *Test:* the go's scope is quoted
  where the call is logged.

