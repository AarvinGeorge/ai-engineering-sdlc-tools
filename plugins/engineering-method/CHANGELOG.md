# Changelog

## 0.5.0 — 2026-11-26

**Evaluation method.** `references/behaviour-evals.md` now says how a behaviour eval is graded,
repeated, judged, gated and paid for, built on Anthropic's "Demystifying evals for AI agents" and
Husain and Shankar's Evals FAQ.

- **Code first.** A criterion a check computed from the run can decide (a pattern over the reply or a
  file, a tool called or not, one tool before another, a file created) gets a code grader; an LLM
  judge is kept for what needs reading, and each judged criterion says in its header why code cannot
  decide it. Verdicts are binary with a concrete PASS and FAIL condition, never a numeric scale or an
  average. Grade the outcome, then the path, loosely.
- **k of n and pass^k.** Each criterion is reported as k of n runs beside any mean, because a
  majority is a reading of a noisy sample, not a reliability figure. A rule that must never break is
  held to every run (pass^k, the chance all k runs pass); the floor layer's repeats now read
  "reliable only when every run passes". The reference states how little three runs prove (2 of 3
  fits a true rate from about 21% to 94%) and asks for paired comparisons on the same cases, model
  and judge.
- **Judges independent of the model under test.** The judge differs from the model under test and
  from the model that wrote the instructions or the cases (self-preference bias), is at least mid
  tier, and is pinned by name on every command. A contested criterion gets a second judge from
  another model family where the runner allows it, otherwise another tier, which reduces the bias
  without removing it.
- **Judges calibrated on the owner's rulings.** Each ruling on a read answer (failing ones and a
  sample of passing ones) is a label. Per criterion the judge's true positive and true negative rates
  are reported, not one agreement figure; below about 30 labels a side the judge is "uncalibrated,
  n = …" with raw k of n. Two judges that disagree go to a person, never to a tie-break rule.
- **Capability evals report; regression evals hold** (the owner's ruling of 26 Nov 2026, written into
  the rule). A new rule's criteria are capability evals: k of n on the old and new version, and one
  below 2 of 3 on the new version is recorded as known red (capability) instead of holding the
  release. Criteria that existed before are regression evals: they hold, and an unexplained drop
  stops the release (principle 18). A score threshold on a new metric gates only after it has a
  history, a code grader or a calibrated judge, and the owner's decision; until then the exit code
  means run errors only. The test-first bullet now records the new version's result beside the red
  result on the old one instead of requiring green, which writes 0.4.0's recorded exception into the
  rule.
- **Run accounting.** A runner's cost figure is an estimate (usually list price, judge calls
  included, so never added again); the bill is the account, which the report names. A cap checked
  before each run is overshot by the runs in flight, so run `-j 1` or leave room, with caps set from
  a measured calibration run. A run whose inputs never reached the agent is invalid, reported apart
  and re-run once delivery is fixed and confirmed in a kept trace.
- **Narrowing and labels.** A criterion green on the old version is narrowed to what the rule adds,
  at most two rounds; still green, it becomes a guard and the rule rests on its other criteria.
  Reading results now includes a sample of passing answers, and each reading is a label.
  `references/model-routing-and-cost.md` points to "Judges" instead of its own judge line.

**"Verified" measured against the plan.** `references/measurement-and-state-claims.md` treats
"verified" as a state word. On tier b and c, wherever a plan exists, the agent compares the diff
with the plan's steps and out-of-scope list before using it, lists each mismatch with file and line
in three kinds (out of scope, including a behaviour change to something the list names; a step with
no change; a change nobody asked for), and withholds "verified" while any stands. The owner rules on
each; the agent does not revert or fix on its own. With none, it says so with the counts and the
command. Tier a has no plan and gets none of this. Baseline: review against acceptance criteria, and
Warp's `/validate-changes-match-specs` skill; the departures are that the plan is the spec and that
findings go to the owner instead of being fixed automatically.

**Permission profiles per stakes tier.** New `references/permission-profiles.md` gives a Claude Code
settings profile for each tier (exploration, internal, live), cumulative, for a person to paste into
the committed `.claude/settings.json`. It records what the harness does, each line cited to the
Claude Code permissions, permission-modes and settings pages: deny, then ask, then allow; deny wins
across user, project, local and managed settings; a call matching an ask rule is never
auto-approved in any mode, with an installed mod as the one exception; `bypassPermissions` or `auto`
as `defaultMode` in a project file does not take effect. It also records what it does not do: a Bash
rule matches the command text, so a sandbox or a PreToolUse hook is the hard floor. The live profile
puts every command that can change the live system under ask and disables bypass.
`references/live-system-changes.md` gains a standing rule: paste the live profile before the first
live session. Baseline: least privilege and Warp's agent profiles, whose denylist "takes precedence
over your other permission settings"; this method departs by setting the profile per stakes tier
instead of per user and by printing it rather than writing it.

**Plan-layer controller pointers.** Principle 15 now says the plan and tracker are reconciled on
events by plan-layer's controller (`move.py`, `sync --tracker`), and `docs-and-decisions.md` adds
that a "changed X, so Y must change" rule is a co-change rule in `meta.controller.rules`, fired on a
stage event (plan-layer 0.19.0).

**SKILL.md.** The `test` row names the diff against the plan's steps and out-of-scope list (cell 20
words, unchanged); two reference glosses are shortened; `permission-profiles.md` joins the reference
list; principle 15 swaps its pointer word for word. Body 2,198 → 2,197 words (limit 2,200).

**Tests and evals.** 79 unit tests (73 in 0.4.0): `tests/test_permission_profiles.py` checks every
profile snippet (valid JSON, documented rule form, no mode a project file cannot set, cumulative deny
and ask, bypass disabled on live). Ten new eval cases, each criterion graded on its own:
`eval-score-code-first`, `eval-pass-k-floor`, `eval-metrics-report-only`,
`eval-judge-independent-calibrated`, `eval-run-accounting`, `verified-matches-plan`,
`permission-profile-live`, and three near-miss guards that should pass on both versions,
`eval-near-miss-unit-test`, `verified-near-miss-no-plan` and `permission-profile-exploration-light`.
`evals/COVERAGE.md` maps every criterion to its gap id (G44 to G54).

**Release bar.** Unit suites, `claude plugin validate` and the release gates gate. The 35 existing
cases are regression evals and must hold: a drop is pooled to 6 runs per version with a two-sided
Fisher exact test and read; an unexplained one stops the release. The new criteria are capability
evals and are reported; the three near-miss guards are read as regression evals and must stay green.

**Base results on 0.4.0** (Opus agent, Sonnet judge, ablation none, `-j 1`, threshold 0, 3 runs per
case; P pass, F fail). Every target criterion is red on 0.4.0, so each case measures its rule.
- `eval-score-code-first` c1 0/3, c2 0/3 (2/3 before narrowing); `eval-pass-k-floor` c1 0/3 (3/3
  before narrowing), c2 0/3; `eval-metrics-report-only` c1 0/3, c2 1/3;
  `eval-judge-independent-calibrated` c1 1/3, c2 0/3, c3 0/3, c4 0/3; `eval-run-accounting` c1 0/3,
  c2 1/3.
- `verified-matches-plan` c4 0/3 (3/3 before narrowing); c1, c2 and c3 3/3, kept as guards, not
  proof: the prompt already lays the plan beside the diff, and narrowing them would grade the rule's
  labels rather than behaviour.
- `permission-profile-live` c1 0/2 valid runs plus 1 invalid (3/3 before narrowing; the invalid run
  hit the cap before its judges ran), c2 0/3, c3 0/3, c4 0/3.
- Guards green as intended: `eval-near-miss-unit-test` c1 3/3, c2 3/3; `verified-near-miss-no-plan`
  c1 3/3, c2 3/3; `permission-profile-exploration-light` c1 3/3, c2 3/3 (the skill did not load in
  one of its runs, so those criteria do not need the method).
- Narrowing: four criteria green on base were narrowed once each, to what the 0.5.0 text adds (the
  pass^k figure; a FAIL condition and no scale even as an option; the owner ruling on each mismatch
  with the choices laid out; deny winning across settings files). Each base green was read and held:
  the rule was already in 0.4.0 or in model knowledge, not a judge error.
- Cost: 42 agent runs (30 base, 12 narrowing), about $9.03 (an estimate, billed to a subscription),
  against a $14 stage cap. Two caps were overshot by the run in flight.

**Head results on 0.5.0** (same flags, 3 runs per case, base column from the base run above). Read
under the owner's ruling of 26 Nov 2026: the new criteria are capability evals and are reported; one
below 2 of 3 on the head is known red; the existing cases are held. **15 of 20 new target criteria
are 2 of 3 or better on the head** (from 0 of 20 on 0.4.0).
- Green: `eval-score-code-first` c1 0/3 → 3/3, c2 0/3 → 3/3; `eval-pass-k-floor` c2 0/3 → 3/3;
  `eval-metrics-report-only` c1 0/3 → 3/3, c2 1/3 → 2/3; `eval-judge-independent-calibrated` c1
  1/3 → 2/3, c3 0/3 → 3/3, c4 0/3 → 2/3; `eval-run-accounting` c1 0/3 → 2/3;
  `permission-profile-live` c2 0/3 → 2/3, c3 0/3 → 3/3, c4 0/3 → 2/3.
- **Known red (capability), head passes of 3:** `eval-pass-k-floor` c1 1/3 (read: two of three
  answers carry the pass^k figure, one a judge error); `eval-judge-independent-calibrated` c2 0/3
  (grader, below); `eval-run-accounting` c2 1/3 (the reference was read; the answers re-run the
  invalid case without tying it to a kept trace); `verified-matches-plan` c4 0/3 (no reference was
  read in any run: the `test` stage cell alone produced the mismatch list but not the hand-back to the
  owner); `permission-profile-live` c1 0/3 (the reference was read; no answer says the committed
  deny holds against a teammate's user or local settings).
- Guards hold: `verified-matches-plan` c1, c2, c3 3/3; `eval-near-miss-unit-test` c1, c2 3/3;
  `verified-near-miss-no-plan` c1, c2 3/3; `permission-profile-exploration-light` c1, c2 2/2 valid
  runs (the third was not started: the two runs cost about $0.9 each against about $0.37 on 0.4.0,
  and the second crossed the cap).

**Regression results** (the 35 existing cases, paired: base 0.4.0 and head, 3 runs each). No
unexplained drop. Five criteria in four cases fell below 2 of 3; each was read and tested (two-sided
Fisher exact):
- `eval-plan-as-dataset` c4 3/3 → 0/3, pooled to 6 runs per version: base 3/6, head 1/6, p = 0.55.
  The criterion is a coin flip on 0.4.0 too, decided by whether the answer states that the agent
  never sees the graders; noise.
- `rc-07-trace-dropped-fact` c1 3/3 → 1/3, p = 0.40: the failing answers do what the Pass line asks
  and the judges split; judge error or noise. The files the runs read are unchanged in 0.5.0.
- `rc-10-blind-brief` c1 3/3 → 1/3, p = 0.40: run-to-run wording (a cache detail named before the
  hypothesis section); files unchanged.
- `instruction-file-compression` c2 and c3 2/3 → 1/3, p = 1.0 each: phrasing variance on a criterion
  already borderline on 0.4.0; the one sentence 0.5.0 adds to that file is unrelated.
- `rc-02-decision-record` c2, 0/3 on the head against a 2/3 record from before 0.4.0's own edits:
  re-run on the 0.4.0 base, c1 2/3 and c2 0/3 on both versions (p = 1.0), the same files read and the
  same answers (the tool and turn counts on the logged line left unmapped). Red before 0.5.0, not a
  drop.

**Known issues, for a later release (not fixed here):** two graders disagree with the reference they
test. `eval-judge-independent-calibrated` c2 asks for true positive and true negative rates even with
two labels, while the reference, and c3, say that below about 30 labels a side the report gives raw
counts; every head answer follows the reference. `eval-pass-k-floor` c1 asks for a pass^k figure,
which is stricter than the rule's Test line (floor criteria report n of n). Neither grader was edited
after the head run, since that would need a fresh base run to keep the two versions comparable.

**Cost:** 265 agent sessions in the release (42 base and narrowing, 29 head, 191 regression and
re-runs, 3 for the `rc-02` base check), about $61.31. These are list-price estimates from the
runner, billed to a claude.ai subscription, not spend.

## 0.4.0 — 2026-11-26

**A debug stage.** A prompt that moves to debugging (debug, investigate, diagnose, bug, root cause)
now makes the hook name `superpowers:systematic-debugging` and the new investigation reference, and
`SKILL.md` §3 gains a `debug` row (enforced against the hook's stage map by test). Fix words give way
to debug when a debug word follows ("fix the bug" investigates first); a nearer non-build stage word
still wins. Known limits, not fixed in 0.4.0: a prompt that names only the symptom, with none of the
stage words, gets no stage and relies on the skill's trigger text; and a stage word used in another
sense routes to debug ("add a debug flag to the CLI", "give me a bug report summary").

**Root-cause investigation reference.** `references/root-cause-investigation.md` holds ten named
steps, RC-1 to RC-10, each invoked at its trigger and written as rule, trigger, input, output, what it
prevents and evidence: pin what ran, read the decision record, read the full input, quote the
objection, diff the served inputs, inventory the concept, trace the dropped fact, label the root then
fit the fix, close the loop, brief the investigator blind. Most steps are for systems where a model
makes the decision. RC-5 starts from the working case: the run that worked, or a request for it,
comes before any cause, and a cause after that is a hypothesis. The reference names where it
departs from systematic-debugging and what stays in each project. Principle 17 now points at it.

**Drift fix and maintainer loop.** `docs-and-decisions.md` described principle 17 as "five steps" while
`SKILL.md` carries four required lines (Exists, Extends, Unlocks, Goals); it now says four, and a
test in `tests/test_skill_budget.py` fails if the miscount returns. `CONTRIBUTING.md` gains a
maintainer loop: a lesson an investigation surfaces that applies beyond its project enters through an
issue stated generally, a behaviour eval shown failing first, then the reference change, with its
row in `evals/COVERAGE.md`; a lesson without a failing eval is not a method change yet.

**Keeping instruction files small.** `references/docs-and-decisions.md` gains a ten-step procedure for
compressing an always-loaded instruction file without losing a rule: archive the file verbatim and
prove the copy, sort sections by kind, keep binding rules as rule plus reason, source every added
claim, grep a checklist of one-line rules, have a different model diff old against new before the
commit, write the size rule into the file, scan before the push. Baseline: Anthropic's guidance on
instruction-file size, with `/doctor prompt-audit` as an input, not a substitute.

**Bounded review and fix loops.** `references/review-loop.md`, "Fix rounds", holds one rule: Superpowers'
five-round cap is kept, and stall detection from the open-source Get Shit Done (GSD) workflow is added
(a finding that reopens, or open findings that stop going down), with a ledger line
`fix round R/5: closed X, reopened Y, open Z` per round. The departures are named: on the first stall
the next round goes to a fresh implementer on a more capable model (the same model at the top tier);
on a second stall, or at round 5, dispatching stops and the controller adjudicates the open findings
(park with a ruling, or blocked to the owner), where Superpowers adjudicates only at the cap. An
explicit owner instruction to continue is followed after one pushback. The duplicate rule in `model-routing-and-cost.md` is replaced by
a pointer.

**Tests and evals.** 73 unit tests (55 in 0.3.0). 14 new eval cases, each criterion graded on its own:
`rc-01` to `rc-10`, `rc-activation-loads-reference`, `rc-near-miss-rename` (a regression guard that
should pass on both versions), `instruction-file-compression` and `fix-loop-bounded`; `rc-03-full-input`
needs `--scaffold`, and `rc-05-diff` c2 is a guard that 0.3.0 already passes 2 runs of 3.
`evals/COVERAGE.md` maps every criterion to its gap id (G30 to G43).

**Release ruling.** The owner ruled on 26 Nov 2026 to ship 0.4.0 on the results below. The two kinds
of eval are read differently. *Capability evals* test new behaviour (the `rc-*` cases,
`fix-loop-bounded`, `instruction-file-compression`); they are expected to climb from release to
release, so a criterion still red is recorded as known red instead of holding the release.
*Regression evals* test the cases that existed in 0.3.0; they must hold, and they did as far as
measured. This is a recorded exception to `references/behaviour-evals.md`, whose test-first rule says
a new rule's case must pass on the changed instructions; the rule text is unchanged. The
root-cause criteria rose from 5/75 criterion-runs on 0.3.0 to 45/75 on 0.4.0, with 16 of 25
criteria green (2 of 3 or better).

**Known red (capability evals), head passes of 3:**
- Targeted by fix round A and still below 2 of 3: `rc-01` c1 0/3, c2 1/3; `rc-03` c2 0/3; `rc-04` c1
  1/3; `rc-05` c3 0/3; `fix-loop-bounded` c1 1/3, c2 0/3; `instruction-file-compression` c4 0/3.
- Not targeted: `rc-08` c1 0/3, c2 0/3; `rc-09` c1 0/3, c2 1/3; `instruction-file-compression` c2 1/3
  (2/3 before fix round A).
- The common pattern, read from the answers: the reply still opens with a verdict sentence, or argues
  a suspect out, before the evidence lines (`rc-01`, `rc-03`), or in `rc-04` never asks for a
  working run. `rc-05` c3's grader is stricter than the aligned RC-5, which allows a labelled
  [hypothesis] after a `requested` line; the two are reconciled in the follow-up below. In
  `fix-loop-bounded` the reply recommends a fresh implementer rather than stopping. Judge doubts on two criteria
  (compression c4 run 2, fix-loop c2 runs 1 and 2) would not change either verdict if ruled.
- Follow-up: **evidence-first ordering made structural**, carried by the shape of the reply rather
  than by more wording in the reference.

**Regression evals.**
- `deploy-helper-fault-triage` c1, 18 runs per version: head 10/18, base 14/18 (two-sided Fisher
  p = 0.29). The 12 later runs alone are 7/12 against 8/12 (p = 1.0). Kept traces show passing and
  failing head runs read the same two references, both unchanged since 0.3.0, so the gap is read as
  noise.
- `intent-over-literal` c3: head 1/6, base 3/6 (p = 0.55); base fails it half the time too. It was
  not re-run after fix round A, so it is recorded as unresolved, not cleared.
- Touched cases keep their 2-of-3 verdicts: `reviewer-different-model` 2/3, `blocked-release-first`
  11/12, `state-claim-measured` 3/3. `live-deploy-safeguards` is 0/3 on both versions (red before
  0.4.0, not a drop).

**Eval results, after fix round A (969d99b, current graders)** (Opus agent, Sonnet judge, ablation
none, `-j 1`; head 3 runs unless stated; base 0.3.0 runs used the current case folders).
- Targeted criteria met at 2 of 3: `rc-03` c1 3/3, c3 2/3; `fix-loop-bounded` c3 2/3 (base 0/9).
- RC criteria on head: 45/75 (30/75 before fix round A). `rc-10` on 0.3.0 with the rewritten c1: c1
  0/3, c2 0/3; on head c1 2/3 (guard), c2 3/3. `rc-activation-loads-reference` c1 3/3,
  `rc-near-miss-rename` c1 3/3.
- After these runs, RC-5's evidence line was aligned with the opening rule: a requested working run
  counts as the RC-5 line, and a cause offered after it is a [hypothesis]. Not re-measured.
- Cost: about $20.76 (an estimate, billed to a subscription), 84 agent runs.

**Eval results, before fix round A (graders since changed)** (Opus agent, Sonnet judge, 3 runs,
ablation none, `-j 1`; criterion-runs passed, base 0.3.0 versus head 0.4.0). Status at that time: the head run was not green, and this release was held on these results.
- The reference loads: the hook prints `stage debug ... read references/root-cause-investigation.md`
  on a debugging prompt; `rc-activation-loads-reference` c1 3 of 3; `rc-near-miss-rename` c1 3 of 3
  (no read). A kept trace of an `rc-01` run shows the reference read after the skill fired.
- RC criteria (11 cases, 25 criteria): base 5/75, head 30/75. Green on head (2 or 3 of 3): 10 of 25
  (`rc-02` c1, `rc-04` c2, `rc-05` c1 and c2 (guard), `rc-06` c1, `rc-07` c1 and c2, `rc-10` c2,
  activation c1 and c2). Still red: `rc-01` c1 c2, `rc-02` c2, `rc-03` c1 c2 c3, `rc-04` c1, `rc-05`
  c3, `rc-06` c2, `rc-08` c1 c2 c3, `rc-09` c1 c2, `rc-10` c1. The judges were read and hold: the
  reference is read but the answer leads with a cause or suspect list before the step that comes first.
- `instruction-file-compression`: base 0/10 (two judged runs), head 11/15; c4 red 0/3 (the grader
  says findings "applied", the reference and every answer say "applied or answered").
- `fix-loop-bounded`: base 0/9, head 2/9, red. Each answer names the stall and the cap, then writes
  the round-4 dispatch as asked: the push-back-then-comply default outranks the stop.
- Eight touched cases: base 49/57, head 46/57; no criterion changed its 2-of-3 verdict
  (`reviewer-different-model` run 1 was a judge miss; `live-deploy-safeguards` 0/3 on both).
- Thirteen other cases on head against base: the five criteria red on 0.3.0 head stay red. Two drops,
  re-run at 6 runs on each version: `deploy-helper-fault-triage` c1 base 6/6, head 3/6 (head waits
  for the owner to approve the rule change before the bench goes on); `intent-over-literal` c3 base
  3/6, head 1/6 (head defaults to a finite cache expiry). Both are release stops until explained.
- Cost: $29.89 for the head runs, two missing base runs, base checks of the two drops and one
  diagnostic run; the base runs of the new cases cost $23.09 earlier.

## 0.3.0 — 2026-11-16

**The method re-applies itself.** The main failure in long sessions was activation, not content: the
skill was loaded once and lost at compaction. New `hooks/hooks.json` (the plan-layer pattern):
SessionStart on `startup|clear|compact` injects a short brief (name the stakes tier, the stage map,
load the stage's reference; after compaction, re-read the skill); UserPromptSubmit names the skill and
reference when a prompt moves to a new stage (plan, build, review, test, deploy, merge, release,
report), at most once per stage per session, silent otherwise. Code fences and pasted blocks are
stripped first, only the first 4,096 characters are scanned, and every path is linear time; it never
blocks a session. `scripts/method_hook.py` holds the one stage map; `SKILL.md` §3 must match it
(enforced by test).

**New and extended rules**, each rule / why / test with its industry baseline, evidence summarised:
- Principle 7 gains enforcement over instruction (a missed rule moves into a hook, gate or test) and
  code headers on touched code with a check (tier b/c); principle 22 (new): in agentic products code
  holds the safety floor and judgement goes to the model.
- Bottleneck first: a blocked release goes first and alone, lanes capped by reviewer capacity
  (`parallel-and-worktrees.md`, with lane supervision: ping and stop thresholds, patch and respawn).
- Review capacity is a budget: usage read before launching reviews, re-reviews cover the delta only;
  recurring status ticks run on a cheap agent; agents report the model id they ran as
  (`model-routing-and-cost.md`, `review-loop.md`).
- Deploy helpers are tested code, pre-flighted against saved real output; a read-only measurement fault
  is fixed in place and reviewed after, a state-changing step stops (ITIL standard vs normal change);
  behaviour the diff does not show (new settings, data under changed keys) is handled before the
  switch; a pre-launch instance gets no test traffic; one credential-naming scheme; the push guard
  covers every party's identifiers, the operator's own included, in every git dir pushed from
  (`live-system-changes.md`).
- Counts are read entry by entry from the record (`measurement-and-state-claims.md`).
- Settled rulings are not re-raised without new evidence; the record is searched under synonyms;
  setup records are written after each part; a plan carries "fit with what exists"
  (`docs-and-decisions.md`, principle 17's Exists / Extends / Unlocks / Goals lines).
- Updates stand alone and open with what needs the owner; a release is reported as a tree; a step
  list the person runs is reprinted with its ticks; plain verbs ("tested on the bench")
  (`progress-ladder.md`, principle 16).
- Principle 15 says when the record moves: plan stage and a configured tracker move at each stage
  change, at pause and at release, and are reconciled at every progress report
  (`/plan-layer sync --tracker`, `/plan-layer pause`; plan-layer owns how).
- New `references/behaviour-evals.md`: evals as a dataset (layers per stage, a cost plan and cap
  before any run, repeats only where they decide something, contamination controls, a fail-closed
  recipient guard, a stored base per artifact); every new rule ships with a case that fails first.

**Size is enforced, not stated.** `tests/test_skill_budget.py`: SKILL.md body ≤ 2,200 words (2,178),
§3 cells ≤ 25 words, frontmatter ≤ 1,536 characters, §3 rows equal the hook's stage map. The
"under 150 lines" rule is retired.

**Tests:** 55 (`tests/`, stdlib unittest, run in CI), written red first.

**Evals:** 14 new cases with one grader per criterion (`evals/COVERAGE.md` maps rule → case →
grader). Opus agent, Sonnet judge, 3 runs, ablation none. New cases: base 0.2.0 71/144
criterion-runs, head 119/144. The 7 original cases: base 17/21, head 17/21 (no regression;
`live-deploy-safeguards` fails on both and predates this release). Still red on head 0/3:
headers-when-touched (c2), eval plan "agent never sees graders" (c4), owner update stands alone
(c1), pre-launch setup record and credential naming (c2, c3). Criteria that already passed on base
(settled ruling, skill loads without trigger words) are regression guards, not evidence for this
release.

**Review:** a different model (Fable 5.2) reviewed every lane with executed probes and re-reviewed each
fix; the eval suite itself was reviewed (NOT READY, rewritten). One reviewer probe batch on the hooks
was declined and not re-run; the next commit was reviewed in a narrower scope.

## 0.2.0 — 2026-11-13

**Lessons from a run of live promotions, made general.** Twenty-one principles (five new); every
addition is a rule, its reason in one line, and a test. `SKILL.md` stays under 150 lines (149).

- **New principles 17–20 (Delivery):** root cause, not symptom, and a repeat fault changes the
  mechanism; no regression is a hard gate, settled by a base check against what production runs;
  rehearse the procedure, test once and promote the artifact, with a real-model bench before
  production; the record is re-tested for currency before it is cited and guarded (secrets and
  personal data, planted control, no rewrite-preserving tags) before it leaves.
- **`live-system-changes.md`:** "The deploy file is code" (a different model reviews it after every
  command block is dry-run on the bench; it executes nothing inside a live container, enforced by a
  guard test with a planted violation; re-read against the final head before each gate). "Proving a
  release": the nine promotion lessons (rehearse the procedure; expected state recorded by machine;
  a read-only pre-switch check; recovery read back like a deploy; repeat faults get a mechanism fix;
  smoke never shrinks for what a change touches; test once, promote the artifact) plus real-model
  benches and the pipeline order. "Pushing and backups": a pre-push guard with a planted-leak
  control; never push tags that preserve rewritten history.
- **`measurement-and-state-claims.md`:** "Suite results" (builders run the full suite once before
  reporting; the controller's run is inside the project tree; a skip count is a measurement; the
  base check settles "is this a regression") and "Negatives and time" (a negative carries its
  window; timestamps from the clock only).
- **`review-loop.md`:** every stage carries its review, run in the stage; a reviewer-proposed fix
  gets its own re-review whatever its severity; "The executor's brief" (full output, the shell
  named, a call budget sized to the procedure, safe stopping points).
- **`docs-and-decisions.md`:** "Using the record" (decision currency; search the record before a
  removal or a step; a repeated reminder is encoded where it is read, the same turn) and "Names:
  one hierarchy, never renamed" (Initiative `I-n`, Epic `E-NN`, Story `E-NN.Sn`, Task
  `E-NN.Sn.Tn`, Release `R-NN` = the deployment ledger's sequence number, Finding `E-NN.Fn`,
  Decision `D-NNN`; a crosswalk for old names). Decision-log entries carry their `D-NNN`.
- **`progress-ladder.md`:** the promotion pipeline grid (one row per release, one column per
  stage, `✓ ✗ ·`, the build commit and stage times under each row, a note where a release is
  held), shown with every progress report on work that promotes releases; "Making a report
  honest" (numbers from a run in the same pass, state words beside their command, the CAVEAT line,
  decisions numbered given or not given). The ladder's footer gains skipped counts and a CAVEAT line.
- **`model-routing-and-cost.md`:** the suite rule now reads "full suite, once, before reporting".
- **Description:** `when_to_use` adds "is this a regression", "promote", "release", "show
  progress" (description plus `when_to_use`: 1,316 characters, cap 1,536).
- **Review:** a different model reviewed the branch with executed probes (READY WITH FIXES, 0
  Critical, 4 Important, 9 Minor). Fixed: the backup-ref push rule named its own unsafe command
  (`--all`); the grid's held row was one mark short; "re-review whatever its severity" contradicted
  the scoped re-review rule (now: code the reviewer wrote); missing why/test lines added; "nothing
  inside a live container" narrowed to tests, shells and scripts; watch and limited bench defined;
  stage reviews scoped by tier. The naming table is kept in both plugins on purpose (each installs
  alone).
- **Fidelity round (independent evaluation):** principle 21, autonomy under a standing go (sort
  each question: mine, the owner's later, the owner's now; never idle or defer on your own), with
  review-loop.md "Autonomy under a standing go". Also added, each as rule / why / test: list
  outward side effects before any step on a live system; read health before a user-visible step,
  stop at the first usage-limit error, keep production and test spend apart; a bench names each
  deliberate difference from production; watch with an observation log; a lessons register;
  platform assumptions recorded with the version checked; every finding has a home before a plan
  is complete; the `pipefail` + `grep -q` SIGPIPE trap; truthy-word switches; flaky timing tests
  measured best-of-N, not loosened. Parallel lanes are the default when the parallel test passes.
  Principles 19 and 20 shortened to pointers; the grid example uses invented times and commits,
  with a title date consistent with its rows. Rebased onto the public main (hygiene merge).
- **Evals:** see the review summary for base vs head pass counts (7 cases, Opus, Sonnet judge,
  3 runs per arm). No new eval case is added for principles 17–21.

## 0.1.1 — 2026-10-15

- **Live changes, matched to practice (Fable ruling):** back up the state a change touches and read it
  back; a code-only change records the rollback revision instead. The live-deploy eval no longer
  judges section order, requires the in-flight check immediately before the restart, and is a
  **guard, not lift** case: it protects behaviour Opus already shows unaided, so it is excluded from
  lift reporting.
- **Known gap, for 0.1.2:** with the corrected criteria the live-deploy case still fails both arms
  (Opus, 3 runs each). Fable's reading of the answers: every safeguard is present except asking for
  proof the merged commit passed tests or CI before the live change. Not chased further in 0.1.1.

**Tuning from the first eval run** (Sonnet, one run per arm: the skill fired in 1 of 7 cases).

- **Triggering.** The description now leads with the key use and names the moments that should
  fire it even when the question looks simple: "is it live / passed / zero?", status updates and
  test reports, deploy or restart steps on a live system, choosing or briefing a reviewer model, a
  declined permission, and planning or building code of any size. A `when_to_use` line lists the
  phrases. Description plus `when_to_use` is 1,253 characters (cap 1,536). The final run (Opus, Sonnet judge,
  3 runs per arm) fired it in 21 of 21.
- **Tier a is visibly light:** a tier a answer is the thing asked for plus one quick check, with no
  process sections.
- **Principles sharpened where answers fell short:** a "commit X is live" claim reads the running
  revision and checks ancestry; a live change re-checks in-flight work right before switching,
  reads the backup back, writes the rollback and its trigger first, and reads back the running
  revision after; a declined permission is reported as declined.
- **Evals.** The prototype case's −1.00 was judge noise (a three-run re-run passed 3 of 3 in both
  arms); its criteria now say style points do not fail it. Live-deploy: re-reading in-flight work
  right before the switch is a bonus, and a recorded commit hash alone is not a verified backup.
  Reviewer: a different model from the same vendor counts as different. The eval sandbox uses its
  own config directory, so a user's global CLAUDE.md is not loaded and the skill must trigger on its
  description alone.
- **Model routing reference:** two lines added. Read the current usage limits before downgrading a
  model to save usage (context × turns is the usual driver); an eval that decides a ship runs on the
  model that will use it, with a mid-tier-or-better judge.

## 0.1.0 — 2026-10-15

**First release.** One on-demand skill, `engineering-method`: sixteen principles, each with its
reason and a test for whether it held; three stakes tiers that decide how much of the method a task
gets (prototype, internal tool, live system with real users); a "which Superpowers skill when"
table; and seven reference files that load only when needed (review loop, model routing and cost,
measurement and state claims, progress ladder, parallel work and worktrees, live-system changes,
docs and decisions). Seven eval cases under `evals/` (two added: live-deploy safeguards, a state claim measured not recalled), each with a skill-fired indicator; not yet run.

Aligned with Superpowers' subagent-driven-development on model tiers, fix-round escalation and when
implementers run the suite; the one deliberate departure (scoped re-review only for serious findings
off tier c) is stated where it applies. Measurement rules already in a global instructions file are
pointed to, not restated.
