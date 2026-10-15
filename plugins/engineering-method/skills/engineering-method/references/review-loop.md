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

- **Execute, not reason from the diff.** Write probe scripts and run them. On the project this came
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

## Fix rounds

- **One review per task. A scoped re-review only for a Critical, or an Important on a security
  boundary.** Test-only and docs-only fixes are read by the controller from the diff when the
  implementer's report shows red, then green.
- **A fix that adds a check in one branch is usually the wrong shape.** Ask where the property must
  hold and put it there, once.
- **Escalate on failure.** A worker that fails twice is replaced by a fresh one a tier up, never the
  same one retried. Any fix round past the third goes to the strongest model.
- **Record a residual rather than hiding it.** A known limit, stated, is a decision; a hidden one is
  a defect waiting.

## The reviewer's brief

Brief plus diff, never a corpus. Over about 60 KB of diff, split by commit or point the reviewer at
the changed regions only. Name: the intent, the base commit, the specific risks, what must not
regress, the tool-call bound, and "if a command is declined, do not retry, narrow or relocate it;
mark it unverified".
