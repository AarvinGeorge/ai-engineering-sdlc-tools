# The review loop

Superpowers' `requesting-code-review` and `receiving-code-review` say how to ask for and take a
review. This file says who reviews, what they must do, and when to stop.

## Who reviews

- **Never the implementer's model.** A model scores its own output above an equally good one from
  elsewhere (self-preference bias in LLM-as-judge is well documented, alongside position and
  verbosity bias). Same-model review weakens the gate at no saving.
- **At least as strong as the implementer.** Strong implements, the other strong reviews; a
  mid-tier implementer can be reviewed by either strong model.
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
- **Code the reviewer wrote gets its own re-review.** When a fix is taken as code from the review
  (not as a finding the implementer then fixes), the reviewer is its author, so someone else reads
  it, whatever its severity. *Why:* a fix taken as written from a review
  slipped in a regression; the suggestion had been reviewed, the code had not. *Test:* the fix
  diff has its own review row naming a reviewer other than its author.
- **A fix that adds a check in one branch is usually the wrong shape.** Ask where the property must
  hold and put it there, once.
- **Escalate by Superpowers' fix rounds** (`subagent-driven-development`): early rounds resume the
  implementer; later rounds take a fresh implementer at least one tier up.
- **Record a residual rather than hiding it.** A known limit, stated, is a decision; a hidden one is
  a defect waiting.

## The reviewer's brief

Brief plus diff, never a corpus. Over about 60 KB of diff, split by commit or point the reviewer at
the changed regions only. Name: the intent, the base commit, the specific risks, what must not
regress, the tool-call bound, and "if a command is declined, do not retry, narrow or relocate it;
mark it unverified".

## The executor's brief

An agent that runs a procedure (a deploy file, a bench, a migration) needs more than a reviewer:

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
