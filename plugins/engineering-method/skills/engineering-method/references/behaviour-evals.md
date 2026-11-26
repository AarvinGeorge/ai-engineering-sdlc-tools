# Behaviour evals

`superpowers:writing-skills` runs a rule change as test-first (a pressure case that fails, then
passes). This file covers the suite those cases make up: an eval that judges how an agent or a
prompt behaves, with real model calls that cost money on every run.

The industry baseline is eval-driven development: cases are a versioned dataset, scored against a
stored baseline, with sizes like a test pyramid (small and fast on every change, large and slow
before a release), flaky cases quarantined, code graders where possible and an LLM judge where
necessary, checked against a person's verdicts (Anthropic, "Demystifying evals for AI agents";
Husain and Shankar, Evals FAQ). Capability cases start low and are climbed; regression cases sit
near 100%, and a capability case that holds graduates into the regression set.

## Cost plan before any run

- **Write the arithmetic and a hard cap before the first send.** Cases × runs × arms × cost per
  run = the spend per trigger; multiply by how often it fires (per commit, per pull request, per
  release) for the week. Each stage gets a budget, passed to the runner as a cap that stops the run
  (`--max-cost-usd` or equivalent), never a number in a note. *Why:* an eval runner built ad hoc had
  no cap, and the first per-change estimate written down was many times what anyone expected. *Test:* the plan shows the
  sum and the cap per stage, and the runner's command line carries the cap.
- **The agent under test runs on the model that will use it; the judge is chosen by "Judges" below**
  (model-routing-and-cost.md).
- **A runner's cost figure is an estimate; the bill is the account.** Record which account the runs
  bill to (a subscription's usage or an API key). A reported cost is usually list price including the
  judge calls, so never add the judge cost to it again. *Why:* a per-case table once counted the judge
  twice, and a list-price figure was read as money spent. *Test:* the report names the account and
  calls the figure an estimate.
- **A cap checked before each run is overshot by the runs in flight.** Run one at a time (`-j 1`) or
  set the cap with room for the concurrent runs; measure the cost per run on one calibration run, and
  set each case's cap from its own measured cost (cases that read large fixtures cost more). *Test:*
  the command line carries the concurrency and a cap derived from a measured cost.

## The dataset in layers, mapped to stages

| Layer | What | When it runs | Repeats |
|---|---|---|---|
| **Floor** | a handful of cases for the rules that must never break (safety, sends, spend) | every commit that touches the prompt, tools or model | 3–5; reliable only when every run passes |
| **Core** | one or more cases per rule, including a near-miss where the rule should not fire | every pull request | once; repeat only a case whose result differs from the baseline |
| **Extended** | conflicts between rules, long conversations, adversarial pushes | before a release | once; repeat on a difference |

- **Repeats only on the floor or on a difference.** Five repeats of everything multiplies the cost
  to measure noise on cases that agree. *Test:* the plan names which cases repeat and why.
- **A commit that does not touch the prompt, tools, model or judge does not trigger the suite.**
- **Count clean runs only.** A run that errored, timed out or hit the cap is reported separately,
  not counted as a pass or a fail.
- **A flaky case is quarantined, not deleted**: moved out of its layer with a note, fixed, and moved
  back. A criterion that varies on the old version too is flaky, not regressed: pool more runs on
  both versions before calling a drop.
- **A run whose inputs never reached the agent is invalid**, reported apart like an errored run. Read
  a kept trace of one run of each fixture case before counting it. A run invalidated by the harness
  or a fixture is re-run once the delivery is fixed. *Why:* a fixture case was scored on runs that
  never saw their files.
  Classify runs with `python3 <the skill's base directory>/scripts/eval_stats.py runs <result.json> --fixture
  <case>=<path prefix of its inputs>` (one `--fixture` per case with fixture inputs), paste the whole block, every line, as printed, and run it again on the re-run's result to confirm delivery.
  Run it as one plain command that starts with python3 and the full path: nothing before or after it
  (no cd, variable, `;`, `&&`, `|` or echo), so a `python3` allow rule covers it.

## Scoring: code first, a judge only where code cannot decide

- **Grade with a check computed from the run wherever one can decide**: a pattern over the reply or a
  produced file, a tool called or not called, one tool before another, a file created. Use an LLM
  judge only for what needs reading, such as meaning, tone, or whether a reason holds. *Why:* a code
  check is free and gives the same answer every time; a judge costs a call and varies. *Test:* each
  judged criterion says in its header why code cannot decide it.
- **Verdicts are binary, with concrete PASS and FAIL conditions**; no numeric scales and no averaged
  pass marks. *Why:* a scale hides what failed and drifts between judges.
- **Grade the outcome, then the path, loosely.** One criterion on the result, one on the steps that
  matter; never a fixed tool-call sequence, since an agent finds valid paths nobody planned.

## Repeated runs: k of n and pass^k

- **Report each criterion as k of n runs**, beside any mean. A majority verdict (green in most runs) is
  a reading of a noisy sample, not a reliability figure. *Test:* the result table shows k of n per
  criterion.
- **A rule that must never break is held to every run: pass^k**, the chance that all k runs pass
  (τ-bench, Yao et al.). Per-trial 75% gives about 42% over three runs (Anthropic, as above). *Test:*
  floor criteria report n of n, and a floor criterion with any failing run is not called reliable.
  A new floor criterion is still a capability eval for the release; n of n is what lets it be called
  reliable. For a never-break criterion run
  `python3 <the skill's base directory>/scripts/eval_stats.py floor --name "<criterion>" --results <one letter per run, no spaces or commas: P, F or I>`
  (I = invalid, not counted; the base directory is the one the Skill tool printed when the skill
  loaded) and paste the whole block, every line, as printed; do not work the figures out by hand.
  Run it as one plain command that starts with python3 and the full path: nothing before or after it
  (no cd, variable, `;`, `&&`, `|` or echo), so a `python3` allow rule covers it.
- **Small samples prove little.** 2 of 3 is consistent with a true rate from about 21% to 94% (95%
  Wilson interval); even 6 of 6 against 3 of 6 is not a significant difference. Compare versions run
  for run on the same cases, model and judge (paired, as in Anthropic's "A statistical approach to
  model evaluations"), and say how much the numbers can carry.

## Judges: independent, pinned and calibrated

- **The judge differs from the model under test and from the model that wrote the instructions or
  the cases**, at least mid tier; for a contested criterion, use a second judge from a different
  model family where the runner allows one; where it takes one family only (as `claude plugin eval`
  does), a different tier of it, which reduces the bias but does not remove it. *Why:* a model favours its
  own outputs (self-preference bias, Panickssery et al.). *Test:* the run records name the agent, the
  judge and the implementer, and they differ.
- **Pin every judge by name.** A runner's default judge can change under you, and a score is only
  comparable with another from the same judge. *Test:* every command carries the judge model.
- **Calibrate each judge against the owner's own rulings.** When a person reads answers (failing ones,
  and a sample of passing ones, since reading only failures measures only false fails), each ruling is
  a label: answer, criterion, verdict. Per criterion, report the judge's true positive rate (passes it
  on answers the owner passed) and true negative rate (fails it on answers the owner failed), not one
  agreement figure, which a lopsided set inflates. The field's target is 30 to 50 of each per split,
  about 60 to 100 per failure type (Husain and Shankar); start with what reading the runs gives.
  Below about 30 labels a side, call the judge "uncalibrated, n = …" and give its agreement as raw
  k of n, not as a rate. Re-check the labels when the judge model changes. *Test:* each judged
  criterion's report line carries its rates and label count, or "uncalibrated, n = …" with raw counts.
  Compute agreement with `python3 <the skill's base directory>/scripts/eval_stats.py calibrate --labels <labels.csv>`
  (save the labels to a CSV file first if they are not one: columns answer_id, criterion, owner,
  judge) and paste the whole block, every line, as printed; it prints rates only at 30 labels a side.
  Run it as one plain command that starts with python3 and the full path: nothing before or after it
  (no cd, variable, `;`, `&&`, `|` or echo), so a `python3` allow rule covers it.
- **Two judges that disagree go to a person**, and the ruling becomes a label. Never a tie-break rule.
- **A grader that fails sound answers is fixed in the case** by a ruling on which is right, the grader
  or the reference; never by bending the instructions to the grader.

## Capability evals report; regression evals hold

- **A new rule's criteria are capability evals: they are reported and do not hold the release.**
  Show k of n on the old and the new version; a criterion below 2 of 3 on the new version is recorded
  as known red (capability) in the coverage map and the changelog, and is expected to climb from
  release to release.
- **Criteria that existed before the change are regression evals: they hold.** A drop is read and
  ruled on as the next bullet says; an unexplained one stops the release (principle 18).
- **A difference from the base is read, explained and ruled on.** Read the answers behind it, label
  each a judge error or a behaviour change, and bring it to the owner, who decides the release. Unit
  tests, deterministic checks and live checks still gate (principle 18).
- **A score threshold on a new metric gates a release only after it has a history**: stored results
  across several versions, a code grader or a calibrated judge, and the owner's decision that it now
  gates. Until then, run so the exit code means run errors only (for example a threshold of 0) and
  read the verdicts from the result file. *Why:* with three runs and an unchecked judge, a new
  criterion's red is as likely noise or a judge error as a missing behaviour, and an automatic stop
  holds releases on chance; a criterion that already held is what a release must not lose. *Test:*
  the release notes list known-red capability criteria apart from the regression results, and no
  release step fails on a score threshold that has no history.
- **A new rule's case still has to be red on the old version** (below), because that shows the case
  measures the rule; its result on the new version is reported (first bullet).

## Every new rule ships with its eval

- **Test-first, as for code** (the new result is reported, not required). Each new rule comes with
  a case, run on the current instructions, where it should fail, and on the changed ones; both
  results are kept. A case that passes on the old instructions tests nothing new: narrow it (next
  bullet). *Why:* most rules added without one could not be shown to have changed anything. *Test:*
  each rule in the change has its case, with a red result on the old version and the new version's
  result reported beside it.
- **A criterion that passes on the old version is narrowed to what the rule adds**, at most two
  rewrite rounds; still green after that, it becomes a guard, not proof, and the rule rests on its
  other criteria. Each criterion asks only what the prompt lets the agent do, so a pass on the new
  version is achievable; where the user asks for the opposite of the rule, ask for a recommendation,
  or the method's push back once, then do as asked (SKILL.md, opening paragraph) decides the verdict.
- **A stored baseline per artifact.** Each version of the instructions (or prompt, or tool set)
  has its stored result per case; a run compares against the baseline of the version it replaces,
  and the "without" arm is re-run only when that base changes, not on every commit. *Test:* every
  reported difference names both versions.
- **One criterion per grader**, so a failure says which part of the behaviour broke.

## Controls

- **Contamination.** The agent and the judge never see the expected answer; the judge sees the
  criteria and the answer only. Cases are never copied into the instructions under test (the rule
  is written generally; its eval is a scenario the rule was not written from). *Why:* an example
  that matches the case turns the eval into a recall test. *Test:* a search of the instructions for
  each case's distinctive strings finds nothing.
- **Per-lane isolation.** Each run gets a fresh workspace and no shared memory or cache with
  other runs or with the session that wrote the cases.
- **A fail-closed recipient guard on anything that can send.** A case that can send email, chat or
  any outbound message runs behind a guard that allows only allow-listed test addresses; any other address stops the send and fails the run, including when the list is missing or empty. *Why:* a test
  send cannot be unsent (live-system-changes.md, "List side effects first"). *Test:* a planted
  non-listed recipient in a control case is blocked, and an empty list blocks everything.

## Reading results

- **Read the failing answers, not only the score**, and a sample of the passing ones. A judge is wrong
  sometimes; each reading is a label for "Judges" above.
- **Report spend with the result**: the cost of the run beside its pass counts, against the cap.
