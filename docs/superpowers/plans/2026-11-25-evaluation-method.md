# Evaluation method for behaviour evals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** engineering-method 0.5.0 says how to *score* agent behaviour, not only how to run the suite: deterministic checks first and an LLM judge only where code cannot decide; a judge that differs from the model under test and from the implementer, calibrated against the owner's own rulings; pass^k and k-of-n for repeated runs; and metrics that **report rather than gate** until they have a history. Each new rule ships with a behaviour eval written first and shown red on the version it replaces.

**Architecture:** one reference grows, `skills/engineering-method/references/behaviour-evals.md`, in the house form (rule, *Why:*, *Test:*). It is already reached through the `test` stage (hook stage map and SKILL.md §3 row `test`), so no routing changes. SKILL.md is not edited unless the owner says yes to Q1 (principle 18 limited to deterministic and live checks); its body is at 2,198 of 2,200 words after 0.4.0. One sibling reference line changes (`model-routing-and-cost.md`, its judge clause points at "Judges"). Six new eval cases in the existing format (`evals/<case>/prompt.md` + `graders/`), written before the text.

**Tech stack:** Markdown (reference, eval cases), `claude plugin eval` for behaviour evals, Python 3.10+ standard library for the existing unit suites (no new code).

**Tier b (internal).** The toolkit is public and others install it, but building it touches no live system or user data. A push, PR or marketplace publish is a release and waits for the owner's word. Branch `evaluation-method`, named for the capability.

**Sequencing.** engineering-method 0.4.0 (branch `root-cause-investigation`) is unmerged and changes the same plugin, including this reference's neighbours and the eval suite. Its head run was not green and the release is held on those results (its CHANGELOG, "Eval results"). The report-only ruling does **not** lift that hold automatically; 0.4.0 is released or fixed by its own ruling. **This plan builds after 0.4.0 (or its 0.4.x fix) merges to `main`, on top of it.** Task 0 rebases this branch onto that `main`; nothing is built on the current base `5982357` (0.3.0).

**Recommended version: 0.5.0.** It adds method rules and changes what a red behaviour-eval result means for a release (report, not gate), which is a minor-version change in a 0.x line. 0.4.x is kept for fixes to 0.4.0's held reds, so the two do not mix in one changelog entry.

## Global constraints

- Edits: `references/behaviour-evals.md` and new eval cases. Other files touched, and only these: `references/model-routing-and-cost.md` (one clause), `evals/COVERAGE.md` (rows), `CHANGELOG.md`, the version in `plugins/engineering-method/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` and the root `README.md` together (CONTRIBUTING "Versioning and changelogs"); `SKILL.md` only if the owner rules yes on Q1, and then within budget.
- SKILL.md body ≤ 2,200 words and every other `tests/test_skill_budget.py` limit hold. The Q1 edit lands at exactly 2,200 (Task 4).
- No private names, addresses, hosts, tracker links or ids, or project identifiers in any committed file, this plan included (CONTRIBUTING "Pull request checklist"). Eval scenarios are synthetic and in domains unlike the reference's wording.
- Every new rule ships with an eval that fails first (`behaviour-evals.md`, "Every new rule ships with its eval").
- Cite only public sources in the reference. Every cited page is re-read in Task 0 and confirmed or contradicted (principle 3).
- Gate every piped test run: `set -o pipefail` and read the `OK` line (principle 1).
- Commit after each task; each message ends with the session's Co-Authored-By trailer. Before each commit, scan `git diff --cached` for tracker hosts, private project names and personal addresses.
- **Billing line.** Evals run through `claude plugin eval` on the logged-in Claude subscription (or the API key the session uses; record which in Task 2). The runner's `costUsd` is a list-price **estimate** that includes the judge calls, not the plan's usage and not a bill. Estimate: about **94 runs** (about $24 at the measured ~$0.26 per run) without the Q1 edit, about **187 runs** (about $49) with it. Breakdown in section 4.

## Vendor and baseline facts (read 25 Nov 2026; Task 0 re-reads)

From code.claude.com/docs/en/plugin-evals:
- Six grader types. `regex`, `tool_used`, `tool_order` and `file_exists` "are computed from the transcript and files and cost nothing"; `llm` and `baseline` call a judge. "There are no custom-code graders."
- `llm`: "A judge model votes PASS on the rubric in at least two of three votes." The judge sees `last_message` by default; on `trace` it sees the first 12 and last 12 messages.
- `--judge-model`: default is "the model Claude Code uses for background tasks"; pass an alias or a full model id. The page names no non-Claude judge (open question Q3).
- A run's score is the fraction of its graders that passed; a case's score is the mean across runs; `--threshold` defaults to `1.0`; "The with-minus-without delta is reported but never changes the exit code". The runner reports means, not pass^k; per-run grader results are in `aggregate-result.json`.
- `--max-cost-usd`: "A ceiling on the run's list-price cost estimate, not on plan usage. Checked before each run starts … runs that already started finish, so spend can pass the ceiling by those runs." `-j` defaults to 1.
- `costUsd`: "Estimated cost at list price including judge calls". Runs ending on a usage or rate limit "score 0 with no grader results" and the command exits non-zero.
- `context.scaffold_script` runs "only when you pass `--scaffold`".

From engineering-method 0.4.0's eval runs (generalised):
- A base run showed many new criteria already green; each was narrowed to what its rule adds, at most two rewrite rounds, and one was reclassified as a guard rather than proof.
- A fixture case scored on runs where the fixtures never reached the agent (the kept trace showed "No files found"); those runs were invalid, not fails. `scaffold_script` + `--scaffold` fixed delivery.
- `-j 3` let in-flight runs pass a cap; `-j 1` was used after. Per-case cost varied with fixture size (about $0.17 to $0.38 a run), so caps came from each case's measured cost.
- Per-case costs were once double-counted by adding the judge cost to `costUsd`, which already includes it.
- Reading answers found one judge miss (FAIL×3 on an answer meeting every Pass line) and one grader-versus-reference wording mismatch that failed sound answers in 9 of 9 votes.
- Two criteria dropped on head (6/6 → 3/6 and 3/6 → 1/6 pooled over six runs); one was flaky on base too. The method treated both as release stops (principle 18). The owner then ruled (25 Nov 2026): no metric should block a release yet.

From the field (public):
- Anthropic, "Demystifying evals for AI agents" (anthropic.com/engineering/demystifying-evals-for-ai-agents): deterministic graders where possible, LLM graders where necessary, humans to calibrate; capability evals start low, regression evals sit near 100%, a saturated capability eval graduates to regression; pass^k is the chance all k trials succeed (75% per trial gives about 42% at k = 3); do not grade rigid tool-call sequences.
- Husain and Shankar, Evals FAQ (hamel.dev/blog/posts/evals-faq/): error analysis before metrics; binary verdicts, not 1-5 scales; validate each judge against a domain expert by true positive and true negative rates on a held-out split, with 30-50 passes and 30-50 fails per split; one person makes the final quality calls.
- Yao et al., τ-bench (arxiv.org/abs/2406.12045): introduced pass^k; agents were "quite inconsistent (pass^8 <25% in retail)".
- Anthropic, "A statistical approach to model evaluations" (anthropic.com/research/statistical-approach-to-model-evals): report standard errors, cluster them, compare versions by paired differences on the same tasks.
- Panickssery et al., "LLM Evaluators Recognize and Favor Their Own Generations" (arxiv.org/abs/2404.13076): self-preference bias. Cited from memory; Task 0 confirms the id and title or drops the citation.

## 1. Goal and intent

The owner's story: "Evaluation method: code first, calibrated judges, pass^k, report-only until there is history." The method today says how to *plan and run* a suite (cost cap, layers, test-first, contamination, fail-closed sends) and one line on the judge ("mid-tier-or-better"). It does not say which grader to use for what, how many agreeing runs make a result reliable, how far to trust a judge, or what a red result does to a release. 0.4.0's runs met every one of these gaps.

## 2. The rules (what the reference gains)

R1 Code first. R2 Repeated runs: k of n and pass^k. R3 The judge differs and is pinned. R4 Calibrate the judge against the owner's rulings. R5 Report, do not gate, until there is a history. R6 Run accounting (estimates, caps under concurrency, invalid runs). R7 Narrowing a base-green criterion (bounded) and reading results into labels. Full text in Task 3.

## 3. Evals (written first, Task 1)

House format: `prompt.md` (frontmatter `max_turns`, `allowed_tools`, `description` listing the contamination strings), one grader per criterion, `skill-fired.md` indicator copied from an existing case. New in these cases, following R1: every `llm` grader carries a first comment line `# Judged: <why code cannot decide this>`; a criterion code can decide uses a code grader.

Superpowers is absent inside eval runs, and the agent has no web access (`allowed_tools: [Read, Glob, Grep, Skill]`), so a pass depends on what the method's reference says, not on reading the runner docs. Domains are unrelated to the reference text: a changelog, a support macro, meeting summaries, invoice parsing, a slug function. Every prompt that contradicts its rule ends by asking for a recommendation, so the method's "push back once, then do as asked" does not decide the verdict.

**Routing (probed 25 Nov 2026 with `scripts/method_hook.py --prompt` on the 0.4.0 branch):** all six prompt bodies below route to the `test` stage, which names `behaviour-evals.md`. Two earlier wordings misrouted ("release notes" → release, "I built … with Opus" → build). Task 1 Step 7 re-probes every case.

| Case | Rule | Prompt (summary; Task 1 writes it in full) | Graders |
|---|---|---|---|
| `eval-score-code-first` | R1 | Graders for a changelog skill: writes `NOTES.md` with `## v<version>`, runs `make lint` before writing, readable wording; the user proposes one 1-10 LLM judge per item, pass at an average of 7; "What graders do you recommend?" | c1 (llm) items 1 and 2 go to code graders (a regex over the file's contents or `file_exists`; `tool_order` lint before the write), the judge only for item 3, and it says why code cannot decide item 3; c2 (llm) binary pass/fail with concrete conditions, not an averaged scale |
| `eval-pass-k-floor` | R2 | Three runs of a support-macro skill: safety criterion "never quotes a refund amount" P P F, two others P P P and F P P, suite score 0.78; "green at 2 of 3 … I'd like a one-line note saying the safety rule is reliable. What line do you recommend?" | c1 (llm) separates the 2-of-3 majority from reliability, holds the safety criterion to all runs passing (pass^k) and does not call it reliable; c2 (llm) reports k of n per criterion beside or instead of the mean and says three runs cannot pin a rate |
| `eval-metrics-report-only` | R5 | A two-week-old suite with two scored versions (0.71, 0.64); a teammate wants `--threshold 0.8` and the release job blocked on the exit code; "write the CI step and the release-checklist rule you recommend". | c1 (llm) the judged score does not block the release yet: the step keeps the exit code for run errors (e.g. threshold 0) and publishes base beside head; it names when a metric graduates to a gate; c2 (llm) a drop is investigated by reading answers (judge or behaviour) and the owner rules on the release; it names small-sample noise |
| `eval-judge-independent-calibrated` | R3, R4 | "Our meeting-summary skill was written with Claude Opus, and its evals run on Opus too. Set up the eval judging." The user's idea: Opus as judge too "since it's strongest", `--judge-model` left default for cheap criteria; one criterion ("flags decisions that have no owner") the user and judge disagreed on twice; no labels yet. | c1 (llm) the judge differs from the model under test and from the implementer, gives self-preference as the reason, and pins every judge explicitly; c2 (llm) calibration against the user's own rulings on real answers, both passes and fails, measured as true positive and true negative rates per criterion; c3 (llm) until there are about 30 labels a side the judge is reported as "uncalibrated, n = …" with its rates as raw k of n; c4 (llm) the contested criterion gets a second, different judge (a different family where the runner allows, else a different tier, bias reduced not removed) and a human settles their disagreements, the ruling becoming a label |
| `eval-run-accounting` | R6 | Last night: 12 cases × 3 runs, `-j 4`, `--max-cost-usd 5`; JSON `costUsd` 5.62; three runs of a fixture case `parse-invoices` scored 0 with "No files found" in the trace; "I'd count the parse-invoices case as failed. What do you recommend the report says?" | c1 (llm) `costUsd` is a list-price estimate, real spend is read from the account's usage or bill, and the overshoot came from in-flight runs under `-j 4` (the cap is checked before each run starts); it recommends `-j 1` or a cap with room; c2 (llm) the fixture runs are invalid, reported apart from pass and fail, and re-run after fixture delivery is fixed and confirmed in a kept trace |
| `eval-near-miss-unit-test` | guard | "Add a unit test for this function and show it:" then a two-line pure Python `slugify`. | c1 (regex, `last_message`, `match: not_contains`, `flags: i`, pattern `pass\^|llm judge|judge model|--runs`) no eval ceremony; c2 (llm) shows a deterministic unit test with assertions. Guard: expected green on both versions |

**Predicted green on base (hypotheses, settled in Task 2):** `eval-score-code-first` c2 (Opus already prefers binary rubrics); `eval-judge-independent-calibrated` c1 (principle 10 already says reviewer ≠ implementer); `eval-pass-k-floor` c1 (a failing safety run is visibly alarming). Narrowing, if green, is to the part the rule adds: c2 → "and each judged criterion states why code cannot decide it"; c1 (judge) → "and pins the cheap criteria's judge rather than leaving the default"; c1 (pass-k) → "and states the all-runs rate (pass^k) as the reliability number". At most two rewrite rounds per criterion (R7); a criterion still green after that becomes a guard row in COVERAGE, and the rule's proof rests on its other criteria.

**Achievability on head.** Each criterion asks only for what the prompt lets the agent do with Read/Glob/Grep and its answer. `eval-metrics-report-only` asks for a *recommendation*, so the method's "push back once, then do as asked" does not decide the verdict (0.4.0's `fix-loop-bounded` lesson). `eval-run-accounting` passes on head only because R6 states the runner's cap and cost semantics.

**Contamination.** The `description` line of each prompt lists its distinctive strings (`NOTES.md`, `make lint`, `average of 7`, `refund amount`, `0.78`, `help page`, `0.71`, `0.64`, `threshold 0.8`, `meeting-summary`, `flags decisions`, `disagreed twice`, `parse-invoices`, `5.62`, `-j 4`, `slugify`). Task 3's text must not contain any of them; Task 5 greps.

## 4. Runs and cost

Agent `--model opus` (the model that uses the method); judge `--judge-model sonnet` (differs from the agent and from the Opus implementer); `--ablation none`; `-j 1`; `--no-publish --trust-plugin`; `--runs 3`; `--threshold 0` on head and base (this plan's own R5: the exit code then means run errors only, and verdicts are read from the JSON).

- Calibration: 1 run of `eval-run-accounting` on base, `--max-cost-usd 1`. Record `c`. Expect about $0.26.
- New cases: 6 × 3 × 2 versions = 36 runs.
- Rewrites: at most 2 rounds × 3 predicted-green cases × 3 runs = 18 runs (base only).
- Regression without Q1: the existing cases whose prompt routes to the `test` stage (probed 25 Nov 2026 with `scripts/method_hook.py --prompt` on the 0.4.0 branch: `eval-plan-as-dataset`, `owner-update-from-ledger`, `rc-07-trace-dropped-fact`, `test-report-shows-evidence`), base and head: 4 × 3 × 2 = 24 runs. Task 2 re-probes on the merged base.
- Regression with Q1 (SKILL.md changes, so every case may move): all 35 existing cases on head, 3 runs = 105, plus the routed 4 on base = 12.
- Pooling: up to 2 criteria that drop are pooled to 6 runs on both versions, +12 runs. Task 8's reviewer re-run, +3.
- Totals: without Q1, 1 + 36 + 18 + 24 + 12 + 3 = **94 runs (~$24)**; with Q1, 1 + 36 + 18 + 105 + 12 + 12 + 3 = **187 runs (~$49)**. Estimates at list price; the account is the logged-in Claude subscription. Every command carries `--max-cost-usd` = its own runs × that case's measured cost × 1.25, written in the task before the run.

## 5. Fit with what exists

**Exists:**
- `behaviour-evals.md`: cost plan and cap, layers by stage, repeats only on the floor or a difference, clean runs only, quarantine, test-first per rule, stored baselines, one criterion per grader, contamination, isolation, fail-closed sends, reading failing answers, spend beside results.
- Principle 9 (every failure becomes a test), principle 10 (reviewer ≠ implementer, at least as strong, executes), principle 18 (no regression is a hard gate).
- The runner: four free code graders, `llm` with 2-of-3 votes, `--threshold`, `--judge-model`, `aggregate-result.json` with per-run grader results.
- Case `eval-plan-as-dataset` and its four COVERAGE rows.

**Extends:**
- R1 extends "One criterion per grader" with an order: code grader first, judge only where code cannot decide, and a stated reason on each judged criterion.
- R2 extends "Repeats only on the floor" and "Count clean runs only" with what to report from repeats (k of n, pass^k) and how little three runs prove.
- R3 extends the judge bullet in "Cost plan" from "mid-tier-or-better" to independence and pinning, the judge-side form of principle 10.
- R4 is NEW in the method (nothing measures a judge today); it extends "Read the failing answers" by turning each owner ruling into a label.
- R5 changes the meaning of the floor layer: it reports, and graduates to a gate by stated criteria. It extends "A stored baseline per artifact" (history is the baselines over versions) and narrows how principle 18 applies to judged scores (Q1).
- R6 and R7 extend "Cost plan" and "Every new rule ships with its eval" with the run-accounting and narrowing lessons.

**Unlocks:** any project that evaluates an agent (not only this plugin) gets a scoring order, a reliability number, a judge-trust loop that grows from rulings the owner already makes when reading answers, and a release regime where unproven metrics inform instead of block, so held releases are held by a person's ruling rather than by noise.

**Goals:**
- Evidence before assertion: strengthened; k of n and judge rates are shown, not a single mean.
- Cost discipline: kept; code graders are free, and the spend estimate is labelled as an estimate.
- Independence of review: strengthened; it now covers the judge.
- No over-engineering: kept; no scorer service, no script, no CI change; calibration starts with a handful of labels.
- Enforcement over instruction: unchanged in kind; the rules are prose proven by evals, as in 0.4.0. A text-presence unit test would only pin prose.
- No regression is a hard gate: **weakened for judged behaviour scores by the owner's ruling**, said plainly; deterministic tests and live checks still gate (Q1).

## File structure

```
plugins/engineering-method/
├── skills/engineering-method/references/behaviour-evals.md   MODIFY (Task 3)
├── skills/engineering-method/references/model-routing-and-cost.md   MODIFY one clause (Task 3)
├── skills/engineering-method/SKILL.md                        MODIFY only on Q1 = yes (Task 4)
├── evals/eval-score-code-first/{prompt.md,graders/c1-code-graders-first.md,c2-binary-verdicts.md,skill-fired.md}            CREATE (Task 1)
├── evals/eval-pass-k-floor/{prompt.md,graders/c1-floor-needs-every-run.md,c2-k-of-n-reported.md,skill-fired.md}            CREATE
├── evals/eval-metrics-report-only/{prompt.md,graders/c1-report-not-gate.md,c2-drop-read-owner-rules.md,skill-fired.md}       CREATE
├── evals/eval-judge-independent-calibrated/{prompt.md,graders/c1-judge-differs-pinned.md,c2-calibrated-on-rulings.md,c3-uncalibrated-until-enough.md,c4-two-judges-human-triage.md,skill-fired.md}  CREATE
├── evals/eval-run-accounting/{prompt.md,graders/c1-estimate-and-cap.md,c2-invalid-runs-apart.md,skill-fired.md}             CREATE
├── evals/eval-near-miss-unit-test/{prompt.md,graders/c1-no-eval-ceremony.md,c2-shows-unit-test.md,skill-fired.md}           CREATE
├── evals/COVERAGE.md                                         MODIFY (Task 6)
├── CHANGELOG.md                                              MODIFY (Task 6, results filled in Task 7)
└── .claude-plugin/plugin.json                                MODIFY (version, Task 6)
.claude-plugin/marketplace.json, README.md                    MODIFY (version, Task 6)
```

## Lanes and models

One region (one plugin, one reference, one eval folder), so serial, one writer per worktree. Builder **Opus** for the case and reference text (Tasks 1, 3) and the eval runs with answer reading (Tasks 2, 7); **Sonnet** for COVERAGE, CHANGELOG and version (Task 6, the brief carries the literal rows); **Fable 5.2** for every review (plan, cases, reference, whole branch), fresh agent in its own worktree, executing probes, reporting its model id. The judge inside the evals is Sonnet, a different model from the Opus implementer and the Opus agent under test.

---

### Task 0: Plan review, rebase and baseline

- [ ] **Step 1:** Read `git log -1 main` and `plugins/engineering-method/.claude-plugin/plugin.json` on `main`. Expected: 0.4.0 (or 0.4.x) merged. If not, stop: this plan waits.
- [ ] **Step 2:** `git rebase main` on `evaluation-method` (only this plan's commit moves). Record the new base sha here.
- [ ] **Step 3:** `set -o pipefail; python3 -m unittest discover -s plugins/engineering-method/tests 2>&1 | tail -3`. Record the OK count (0.4.0 had 71).
- [ ] **Step 4:** Record the SKILL.md body word count with the counter in `tests/test_skill_budget.py` (needed for Q1).
- [ ] **Step 5:** The plan review (section "Review" at the end), then its fixes.

### Task 1: The six eval cases (before the reference)

**Files:** create the six case folders listed in "File structure". Copy `skill-fired.md` byte for byte from `evals/eval-plan-as-dataset/graders/skill-fired.md`.

- [ ] **Step 1: `evals/eval-score-code-first/prompt.md`**

```markdown
---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
description: "contamination strings: NOTES.md; make lint; average of 7"
---

My plugin has a skill that writes a changelog. I want behaviour evals for three things it must do:

1. Write the entry to `NOTES.md` with a heading `## v<version>`.
2. Run `make lint` before it writes the file.
3. Keep the wording readable for someone who is not an engineer.

My plan: one LLM judge per item, each scoring 1 to 10, and the case passes at an average of 7. What graders do you recommend?
```

`graders/c1-code-graders-first.md`:

```markdown
---
# Judged: whether each grader choice fits its item and the reason given is a judgement over prose.
type: llm
weight: 1
---

Scenario: three items; item 1 is a file with a fixed heading, item 2 is a command run before a write, item 3 is readability.

Pass when items 1 and 2 are graded by checks computed from the run (for example a regex over the contents of NOTES.md or a file-exists check for item 1; a tool-order or tool-used check that the lint command ran before the write for item 2), an LLM judge is used only for item 3, and the answer says why code cannot decide item 3.

Fail when item 1 or item 2 is left to an LLM judge, or when no reason is given for judging item 3.
```

`graders/c2-binary-verdicts.md`:

```markdown
---
# Judged: whether a rubric is binary with concrete conditions is read from prose.
type: llm
weight: 1
---

Scenario: the user proposes 1-10 scores averaged to a pass at 7.

Pass when each judged criterion is a binary pass/fail with concrete PASS and FAIL conditions, and the averaged 1-10 scale is replaced.

Fail when it keeps a numeric scale or an average as the pass rule.
```

- [ ] **Step 2: `evals/eval-pass-k-floor/prompt.md`**

```markdown
---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
description: "contamination strings: refund amount; 0.78; help page"
---

Eval results for our support-macro skill, 3 runs each (P pass, F fail):

| Criterion | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| never quotes a refund amount (safety) | P | P | F |
| greets the customer by name | P | P | P |
| links the help page | F | P | P |

Suite score 0.78. Our rule is that a criterion passing 2 of 3 runs is green, so all three are green. I'd like a one-line note saying the safety rule is reliable. What line do you recommend?
```

`graders/c1-floor-needs-every-run.md`:

```markdown
---
# Judged: whether the answer distinguishes a majority from reliability is a reading of its reasoning.
type: llm
weight: 1
---

Scenario: a safety criterion passed 2 of 3 runs; the user wants it called reliable.

Pass when the answer separates the 2-of-3 majority from reliability, holds the safety criterion to every run passing (the chance all k runs pass, pass^k, or n of n), and does not write that the safety rule is reliable.

Fail when it calls the safety rule reliable or treats 2 of 3 as enough for it.
```

`graders/c2-k-of-n-reported.md`:

```markdown
---
# Judged: whether small-sample limits are stated is a reading of prose.
type: llm
weight: 1
---

Scenario: same as above.

Pass when it reports each criterion as k of n (for example 2/3, 3/3, 2/3) rather than only the 0.78 mean, and says three runs cannot pin down a pass rate.

Fail when it reports only the mean, or treats three runs as measuring the rate.
```

- [ ] **Step 3: `evals/eval-metrics-report-only/prompt.md`**

```markdown
---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
description: "contamination strings: 0.71; 0.64; threshold 0.8"
---

Our plugin's eval suite is two weeks old. Two versions have been scored so far: 0.71, then 0.64 (3 runs per case, LLM judge on most criteria, nobody has checked the judge against our own verdicts). A teammate wants CI to fail the release whenever the suite score drops: `claude plugin eval . --threshold 0.8` and the release job blocks on the exit code.

Write the CI step and the release-checklist rule you recommend.
```

`graders/c1-report-not-gate.md`:

```markdown
---
# Judged: the recommendation's gating stance must be read from the CI step and the rule together.
type: llm
weight: 1
---

Scenario: two scored versions, an unchecked judge, a proposal to block releases on the score.

Pass when the recommended step does not let the judged score block the release yet (for example it runs with a threshold that leaves the exit code for run errors only, and publishes the score with the previous version's beside it), and it states the conditions under which a metric becomes a gate (a history across versions, a code grader or a judge checked against the team's verdicts, and a person's decision).

Fail when the recommended step blocks the release on the suite score or threshold, or gives no condition for later gating.
```

`graders/c2-drop-read-owner-rules.md`:

```markdown
---
# Judged: the handling of a drop is described in prose.
type: llm
weight: 1
---

Scenario: same as above; the score went from 0.71 to 0.64.

Pass when a drop leads to reading the failing answers to tell a judge error from a behaviour change, a named person decides whether the release goes, and the answer says a small number of runs makes such a drop easy to get by chance.

Fail when the drop is treated as settled by the number alone, in either direction.
```

- [ ] **Step 4: `evals/eval-judge-independent-calibrated/prompt.md`**

```markdown
---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
description: "contamination strings: meeting-summary; flags decisions; disagreed twice"
---

Our meeting-summary skill was written with Claude Opus, and its evals run on Opus too. Set up the eval judging. My idea: use Opus as the judge as well, since it's our strongest model, and for the cheap criteria just leave `--judge-model` at its default. One criterion, "flags decisions that have no owner", the judge and I disagreed on twice last week. We have no labelled examples yet.
```

`graders/c1-judge-differs-pinned.md`:

```markdown
---
# Judged: model choice and its reason are stated in prose.
type: llm
weight: 1
---

Scenario: implementer Opus, model under test Opus, proposed judge Opus, cheap judges left at the default.

Pass when the judge is a different model from both the model under test and the implementer, the reason given is that a model favours its own outputs (self-preference), and every judge, the cheap ones included, is pinned by name rather than left at the default.

Fail when Opus stays the judge, no self-preference reason is given, or any judge is left at the default.
```

`graders/c2-calibrated-on-rulings.md`:

```markdown
---
# Judged: the calibration procedure is described in prose.
type: llm
weight: 1
---

Scenario: no labelled examples yet.

Pass when the judge is checked against the user's own pass/fail rulings on real answers from the runs, including both answers the user passes and answers the user fails, measured per criterion as the judge's true positive and true negative rates.

Fail when the judge is trusted without checking against the user's rulings, when only failing answers are labelled, or when agreement is a single overall percentage.
```

`graders/c3-uncalibrated-until-enough.md`:

```markdown
---
# Judged: how a small label set is reported is stated in prose.
type: llm
weight: 1
---

Scenario: no labelled examples yet; labels will come a few at a time.

Pass when, while the label set is small (well under about 30 answers on each side), the judge is reported as not yet calibrated with its label count, and its agreement is given as raw counts (k of n) rather than as a rate presented as settled.

Fail when a judge with a handful of labels is called calibrated or its agreement is reported as a settled percentage.
```

`graders/c4-two-judges-human-triage.md`:

```markdown
---
# Judged: the handling of a contested criterion is described in prose.
type: llm
weight: 1
---

Scenario: the user and the judge disagreed twice on "flags decisions that have no owner".

Pass when that criterion gets a second, different judge (from a different model family where the runner allows, otherwise a different model or tier, said to reduce the bias rather than remove it), a person settles the cases where the two judges disagree, and those rulings are kept as labels for calibration.

Fail when the contested criterion keeps one judge, or disagreements are resolved by a tie-break rule without a person.
```

- [ ] **Step 5: `evals/eval-run-accounting/prompt.md`**

```markdown
---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
description: "contamination strings: parse-invoices; 5.62; -j 4"
---

Last night's eval run: 12 cases × 3 runs, `claude plugin eval . -j 4 --max-cost-usd 5`. The JSON result shows `costUsd: 5.62`. All three runs of the fixture case `parse-invoices` scored 0, and their traces show `Glob resources/**` returning "No files found".

I need a morning report: what we spent against our budget, whether the cap worked, and the suite result. I'd count the parse-invoices case as failed. What do you recommend the report says?
```

`graders/c1-estimate-and-cap.md`:

```markdown
---
# Judged: the explanation of cost and cap is prose.
type: llm
weight: 1
---

Scenario: cap $5, reported costUsd 5.62, concurrency 4.

Pass when it says costUsd is a list-price estimate (the real spend is read from the account's plan usage or bill), explains the overshoot as runs already in flight under -j 4 because the cap is checked before each run starts, and recommends -j 1 or a cap with room for in-flight runs.

Fail when it reports 5.62 as money spent, or says the cap failed without the in-flight explanation.
```

`graders/c2-invalid-runs-apart.md`:

```markdown
---
# Judged: how the runs are counted is stated in prose.
type: llm
weight: 1
---

Scenario: three runs of a fixture case scored 0 because the fixture files never reached the agent.

Pass when those runs are reported as invalid, apart from passes and fails, rather than counted as failed, and they are re-run after the fixture delivery is fixed and confirmed in a kept trace.

Fail when they are counted as failures, or dropped without being reported.
```

- [ ] **Step 6: `evals/eval-near-miss-unit-test/prompt.md`**

````markdown
---
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
description: "contamination strings: slugify"
---

Add a unit test for this function and show it:

```python
def slugify(s):
    return "-".join(s.lower().split())
```
````

`graders/c1-no-eval-ceremony.md`:

```markdown
---
# Regression guard: a deterministic unit test needs no judge or repeated runs. Code decides: a regex.
type: regex
target: last_message
match: not_contains
flags: i
pattern: 'pass\^|llm judge|judge model|--runs'
weight: 1
---
```

`graders/c2-shows-unit-test.md`:

```markdown
---
# Judged: whether the shown code is a sound unit test is a reading of code in prose.
type: llm
weight: 1
---

Pass when the reply shows a unit test with concrete assertions on slugify's output for at least two inputs.

Fail when no test code is shown.
```

- [ ] **Step 7:** `claude plugin validate plugins/engineering-method` exits 0. Grep the current reference for every contamination string: `grep -n -F -e 'NOTES.md' -e 'make lint' -e 'refund amount' -e '0.78' -e '0.71' -e '0.64' -e 'parse-invoices' -e '5.62' -e 'slugify' -e 'flags decisions' -e 'average of 7' -e 'help page' -e 'threshold 0.8' -e 'meeting-summary' -e 'disagreed twice' -e '-j 4' plugins/engineering-method/skills/engineering-method/references/*.md` prints nothing; prove the grep can fire by running it on this plan file (hits).
- [ ] **Step 7b:** Re-probe routing: for each new case, strip the frontmatter and pipe `{"prompt": <body>, "session_id": "<case>"}` to `python3 plugins/engineering-method/scripts/method_hook.py --prompt`. Expected: `stage test` for all six; reword any that is not.
- [ ] **Step 8:** Commit: `engineering-method evals: six evaluation-method cases, written before the rules`.

### Task 2: Base run (RED on the merged 0.4.x)

- [ ] **Step 1:** `git worktree add <scratch>/em-base <Task 0 base sha>`; copy the six case folders in; `diff -r` one of them against the branch (identical).
- [ ] **Step 2:** Record which account the runs bill to (subscription or API key) from `claude` status.
- [ ] **Step 3:** Calibration, cap written first ($1): `claude plugin eval <scratch>/em-base/plugins/engineering-method --case eval-run-accounting --runs 1 --ablation none --model opus --judge-model sonnet -j 1 --threshold 0 --no-publish --trust-plugin --keep-temp --max-cost-usd 1 --json <scratch>/eval-out/cal.json`. Record `c` = that run's `costUsd`. Read the kept trace: confirm the plugin's stage hook fired inside the eval run (its `stage test` text in the session) and whether `behaviour-evals.md` was read; if the hook does not fire there, say so, since routing then rests on the skill's trigger text alone.
- [ ] **Step 4:** Base, cap written first (18 × c × 1.25): same flags, `--case 'eval-*'` selects the six new cases and `eval-plan-as-dataset`; to keep the six only, run one command per case with a cap of 3 × c × 1.25 each.
- [ ] **Step 5:** Per criterion, record P/F per run, k of n, and the run's validity (errored, capped, or invalid input runs reported apart). Expected: every criterion except the guard's at most 1 of 3; the guard 3 of 3 on c1.
- [ ] **Step 6:** Read every answer on a criterion that came back green. Narrow it to what the rule adds (section 3), re-run that case on base, at most two rounds; still green after two becomes a guard (COVERAGE note in Task 6). Commit each rewrite round separately.
- [ ] **Step 7:** Regression base: run the hook router (`echo '{"prompt":"<body>","session_id":"x"}' | python3 scripts/method_hook.py --prompt`) on each existing case's prompt body; list the cases routed to `test`, plus `eval-plan-as-dataset`; run each on base at 3 runs with its cap. Remove the base worktree after.
- [ ] **Step 8:** Write `task-2-report.md` in the run folder with the tables, costs against caps, and narrowings. Fable 5.2 reviews the rewrites (are the base reds honest, is each criterion achievable on head).

### Task 3: The reference

**File:** `plugins/engineering-method/skills/engineering-method/references/behaviour-evals.md`.

- [ ] **Step 1:** Replace the intro's second paragraph:

old:
```
The industry baseline is eval-driven development: cases are a versioned dataset, scored against a
stored baseline, with sizes like a test pyramid (small and fast on every change, large and slow
before a release), flaky cases quarantined, and an LLM judge run with repeats where its votes
disagree.
```
new:
```
The industry baseline is eval-driven development: cases are a versioned dataset, scored against a
stored baseline, with sizes like a test pyramid (small and fast on every change, large and slow
before a release), flaky cases quarantined, code graders where possible and an LLM judge where
necessary, checked against a person's verdicts (Anthropic, "Demystifying evals for AI agents";
Husain and Shankar, Evals FAQ). Capability cases start low and are climbed; regression cases sit
near 100%, and a capability case that holds graduates into the regression set.
```

- [ ] **Step 2:** In "Cost plan before any run", replace the judge bullet:

old:
```
- **The judge runs on a mid-tier-or-better model; the agent under test runs on the model that will
  use it** (model-routing-and-cost.md).
```
new:
```
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
```

- [ ] **Step 3:** In "The dataset in layers", replace the quarantine bullet:

old:
```
- **A flaky case is quarantined, not deleted**: moved out of the gating layer with a note, fixed,
  and moved back.
```
new:
```
- **A flaky case is quarantined, not deleted**: moved out of its layer with a note, fixed, and moved
  back. A criterion that varies on the old version too is flaky, not regressed: pool more runs on
  both versions before calling a drop.
- **A run whose inputs never reached the agent is invalid**, reported apart like an errored run. Read
  a kept trace of one run of each fixture case before counting it. *Why:* a fixture case was scored
  on runs that never saw their files.
```

- [ ] **Step 4:** Insert after "The dataset in layers" (before "Every new rule ships with its eval"):

```
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
- **Two judges that disagree go to a person**, and the ruling becomes a label. Never a tie-break rule.
- **A grader that fails sound answers is fixed in the case** by a ruling on which is right, the grader
  or the reference; never by bending the instructions to the grader.

## Report, do not gate, until a metric has a history

- **A judged behaviour score informs the release; it does not block it** until it has a history: stored
  results across several versions, a code grader or a calibrated judge, and the owner's decision that
  it now gates. Run so the exit code means run errors only (for example a threshold of 0) and read the
  verdicts from the result file. *Why:* with three runs and an unchecked judge, a drop is as likely
  noise or a judge error as a regression, and an automatic stop holds releases on chance. *Test:* the
  release step does not fail on a score, and each gating metric names when it graduated.
- **A difference from the base is read, explained and ruled on.** Read the answers behind it, label
  each a judge error or a behaviour change, and bring it to the owner, who decides the release. Unit
  tests, deterministic checks and live checks still gate (principle 18).
- **A new rule's case still has to be red on the old version** (below), because that shows the case
  measures the rule; a case still red on the new version ships only by the owner's ruling, with the
  result in the changelog.
```

- [ ] **Step 4b:** Edit in place (they contradict the new text). In the layers table, the Floor row's last cell:

old: `| 3–5, the judge's votes must agree |`
new: `| 3–5; every run passes |`

In "Every new rule ships with its eval", the first bullet:

old:
```
- **Test-first, as for code.** Each new rule comes with a case, run on the current instructions, where it must fail, and on the changed ones, where it must pass; both results are kept. A case that passes
  on the old instructions tests nothing new: rewrite it until it fails. *Why:* most rules added
  without one could not be shown to have changed anything. *Test:* each rule in the change has its
  case, with a red result on the old version and a green one on the new.
```
new:
```
- **Test-first, as for code.** Each new rule comes with a case, run on the current instructions,
  where it should fail, and on the changed ones; both results are kept. A case that passes on the old
  instructions tests nothing new: narrow it (next bullet). *Why:* most rules added without one could
  not be shown to have changed anything. *Test:* each rule in the change has its case, with a red
  result on the old version and the new version's result reported beside it.
```

In `references/model-routing-and-cost.md`:

old:
```
- **An eval that decides whether something ships runs on the model that will use it, graded by a
  mid-tier-or-better judge.**
```
new:
```
- **An eval that decides whether something ships runs on the model that will use it, graded by a
  judge chosen as behaviour-evals.md "Judges" says.**
```

- [ ] **Step 5:** In "Every new rule ships with its eval", append after the first bullet:

```
- **A criterion that passes on the old version is narrowed to what the rule adds**, at most two
  rewrite rounds; still green after that, it becomes a guard, not proof, and the rule rests on its
  other criteria. Each criterion asks only what the prompt lets the agent do, so a pass on the new
  version is achievable; where the user asks for the opposite of the rule, ask for a recommendation,
  or the method's "push back once, then do as asked" decides the verdict.
```

- [ ] **Step 6:** In "Reading results", replace the first bullet:

old:
```
- **Read the failing answers, not only the score.** A judge is wrong sometimes; a criterion that
  fails sound answers is fixed in the case, never by bending the instructions to it.
```
new:
```
- **Read the failing answers, not only the score**, and a sample of the passing ones. A judge is wrong
  sometimes; each reading is a label for "Judges" above.
```

- [ ] **Step 7:** Contamination grep from Task 1 Step 7 on the new file: prints nothing. Grep the file for `must pass`, `rewrite it until it fails`, `green one on the new` and `votes must agree`: no hits. Read the file top to bottom once for duplicated rules (each idea once).
- [ ] **Step 8:** Commit: `behaviour-evals: code first, k of n and pass^k, independent calibrated judges, report not gate`. Fable 5.2 reviews the diff with probes (re-reads each cited page; checks every Test line can be checked; greps for duplicated rules).

### Task 4: SKILL.md principle 18 (only if the owner rules yes on Q1)

- [ ] **Step 1:** In principle 18 replace

old: `production runs; an unexplained base-vs-head difference stops the release. *Test:* both runs shown.`
new: `production runs; an unexplained difference stops the release; judged scores report (behaviour-evals.md). *Test:* both shown.`

Measured on a scratch copy of the 0.4.0 SKILL.md (body split as `tests/test_skill_budget.py` does): 2,198 words before, **2,200 after** (+4 added, −2 for "base-vs-head" and "runs"). Re-count on the merged base before committing; if it is over 2,200, stop and show the owner.
- [ ] **Step 2:** `set -o pipefail; python3 -m unittest discover -s plugins/engineering-method/tests 2>&1 | tail -3`: OK, budget test included.
- [ ] **Step 3:** Commit: `engineering-method: principle 18 points judged scores at report-only`.

### Task 5: Head run (results reported, not gated)

- [ ] **Step 1:** The six cases on head, same flags, `--threshold 0`, one command per case, cap 3 × that case's measured base cost × 1.25. Expected: each rule criterion at 2 or 3 of 3; the guard c1 3 of 3.
- [ ] **Step 2:** Regression: the Task 2 Step 7 set on head (and, if Task 4 ran, the whole existing suite on head), caps written first; compare run for run with base; pool to 6 runs on both versions for any criterion that drops.
- [ ] **Step 3:** Read every red answer and a sample of green ones; label each judge-right or judge-wrong (R4 applied to this suite); fix the case if the judge or grader is wrong, the reference if the behaviour is.
- [ ] **Step 4:** Contamination grep again on the final reference.

### Task 6: Coverage, changelog, version

- [ ] **Step 1:** `evals/COVERAGE.md` gains a section "Evaluation method (0.5.0)", one row per criterion: rule, gap id (next free after 0.4.0's last, Task 0 reads it), grader path; guard rows marked so.
- [ ] **Step 2:** `CHANGELOG.md` `## 0.5.0 — <date>`: the rules in one paragraph each; the eval results as k of n per criterion, base versus head, with spend against caps, the account billed and "estimate"; any guard reclassification; under report-only, a red criterion is stated, not a hold.
- [ ] **Step 3:** Version 0.5.0 in `plugin.json`, `marketplace.json` and root `README.md` together.
- [ ] **Step 4:** `set -o pipefail; python3 -m unittest discover -s plugins/engineering-method/tests 2>&1 | tail -3`; `claude plugin validate plugins/engineering-method`. Commit.

### Task 7: Full suites and identifier scan

- [ ] **Step 1:** The three plugins' unit suites under `set -o pipefail`, each showing its OK or passed line.
- [ ] **Step 2:** `git diff main --stat` lists only the files in "File structure".
- [ ] **Step 3:** Identifier scan of `git diff main` and `git log main..HEAD --format=%B` against the list kept outside the repo; plant one listed value in a scratch file to show the scan fires. Expected 0 hits on the branch.

### Task 8: Whole-branch review

- [ ] **Step 1:** A fresh Fable 5.2 reviewer in its own worktree gets the diff, this plan and a blind brief (goal, paths, constraints; not the author's view). It runs the unit suites, re-counts the SKILL.md budget, greps the reference for every case's contamination strings, re-reads each cited public page, checks every *Test:* line is checkable, re-runs one new case on head with a cap of $1, and reports its model id. Findings carry their probe; an unreproduced one is a hypothesis.
- [ ] **Step 2:** Fix rounds per `review-loop.md` (bounded); re-review covers the delta only.
- [ ] **Step 3:** Stop. Push, PR and marketplace publish wait for the owner's word.

---

## Out of scope

- A scorer service, a script that computes pass^k or judge rates from result files, or any metric formulas (faithfulness, tool-call F1): they belong to each project's scorer, parked as their own story.
- Evals in CI: parked separately on judge spend.
- Labelling a calibration set for this plugin beyond the labels Task 5's reading produces.
- A cross-family judge integration outside `claude plugin eval` (Q3).
- Changes to the 0.4.0 cases, their held results, or the 0.4.0 release decision (Q2).
- Any change to Superpowers, plan-layer or work-log; any SKILL.md edit beyond Task 4; any trigger phrase.
- A unit test over the new wording (the evals test the behaviour).
- Push, PR, tag or publish.

## Rulings on the design questions (coordinator, 25 Nov 2026, scope locked)

- **Q1:** Task 4 stays conditional on the owner's yes. If yes, principle 18 is limited to deterministic and live checks, and judged scores point at report-only. Without it, SKILL.md (always loaded) and the reference (loaded at the test stage) disagree, and `eval-metrics-report-only` may stay red on head.
- **Q2:** the report-only ruling does **not** lift 0.4.0's hold automatically. 0.4.0 is released or fixed by its own ruling; this plan only waits for its merge.
- **Q3:** the second judge for a contested criterion is a different Claude tier now, because the runner takes Claude judges only. Stated as "bias reduced, not removed". No new mechanism or script.
- **Q4:** judges are reported as "uncalibrated, n = …", with their agreement as raw k of n, below about 30 labels a side. Labels accumulate in each project's own record, not in this public repo.

## Review

Before Task 1, a fresh Fable 5.2 agent in its own worktree of this repo reviews this plan, executing rather than reading: re-reads the plugin-evals page and each cited public source and confirms or contradicts every fact in "Vendor and baseline facts" (including the self-preference citation and the two Wilson-interval and paired-difference figures, recomputed); checks that no case in section 3 can be answered by recalling the Task 3 text (shared distinctive strings); checks each criterion is achievable on head with the case's tools; dry-runs `claude plugin validate` on a scratch copy holding the six cases; reports findings with file and line and the probe behind each, and its model id. Brief written blind (goal, this file, repo path, constraints).
