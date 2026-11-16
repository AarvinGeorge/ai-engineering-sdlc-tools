# Behaviour evals

`superpowers:writing-skills` runs a rule change as test-first (a pressure case that fails, then
passes). This file covers the suite those cases make up: an eval that judges how an agent or a
prompt behaves, with real model calls that cost money on every run.

The industry baseline is eval-driven development: cases are a versioned dataset, scored against a
stored baseline, with sizes like a test pyramid (small and fast on every change, large and slow
before a release), flaky cases quarantined, and an LLM judge run with repeats where its votes
disagree.

## Cost plan before any run

- **Write the arithmetic and a hard cap before the first send.** Cases × runs × arms × cost per
  run = the spend per trigger; multiply by how often it fires (per commit, per pull request, per
  release) for the week. Each stage gets a budget, passed to the runner as a cap that stops the run
  (`--max-cost-usd` or equivalent), never a number in a note. *Why:* an eval runner built ad hoc had
  no cap, and one proposed scheme cost over a hundred dollars a commit. *Test:* the plan shows the
  sum and the cap per stage, and the runner's command line carries the cap.
- **The judge runs on a mid-tier-or-better model; the agent under test runs on the model that will
  use it** (model-routing-and-cost.md).

## The dataset in layers, mapped to stages

| Layer | What | When it runs | Repeats |
|---|---|---|---|
| **Floor** | a handful of cases for the rules that must never break (safety, sends, spend) | every commit that touches the prompt, tools or model | 3–5, the judge's votes must agree |
| **Core** | one or more cases per rule, including a near-miss where the rule should not fire | every pull request | once; repeat only a case whose result differs from the baseline |
| **Extended** | conflicts between rules, long conversations, adversarial pushes | before a release | once; repeat on a difference |

- **Repeats only on the floor or on a difference.** Five repeats of everything multiplies the cost
  to measure noise on cases that agree. *Test:* the plan names which cases repeat and why.
- **A commit that does not touch the prompt, tools, model or judge does not trigger the suite.**
- **Count clean runs only.** A run that errored, timed out or hit the cap is reported separately,
  not counted as a pass or a fail.
- **A flaky case is quarantined, not deleted**: moved out of the gating layer with a note, fixed,
  and moved back.

## Every new rule ships with its eval

- **Test-first, as for code.** Each new rule gets a case that runs first against today's
  instructions and fails, then passes with the change; both results are kept. A case that passes
  on the old instructions tests nothing new: rewrite it until it fails. *Why:* most rules added
  without one could not be shown to have changed anything. *Test:* each rule in the change has its
  case, with a red result on the old version and a green one on the new.
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
  any outbound message runs behind a guard that allows only listed sandbox recipients; anything else
  blocks the send and fails the run, including when the list is missing or empty. *Why:* a test
  send cannot be unsent (live-system-changes.md, "List side effects first"). *Test:* a planted
  non-listed recipient in a control case is blocked, and an empty list blocks everything.

## Reading results

- **Read the failing answers, not only the score.** A judge is wrong sometimes; a criterion that
  fails sound answers is fixed in the case, never by bending the instructions to it.
- **Report spend with the result**: the cost of the run beside its pass counts, against the cap.
