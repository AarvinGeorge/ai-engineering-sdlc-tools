# engineering-method 0.5.0 integration plan (evaluation method, plan conformance, permission profiles, controller pointers)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** one engineering-method release, **0.5.0**, carries three pieces of work that were planned and reviewed separately, plus two deferred text edits:

- **(a) Evaluation method**: `2026-11-25-evaluation-method.md` (here "EV"), Tasks 0-8.
- **(b) Plan conformance at "verified" (A) and a permission profile per stakes tier (B)**: the engineering-method lane of `2026-11-25-warp-adoptions.md` (here "W"), Tasks 0-EM and 1-7, with the EM parts of Task 11. Lane PL (runnable invariants) already shipped as plan-layer 0.20.0 and is out of scope here.
- **(c) The deferred 0.4.1 edits** from `2026-11-25-tracker-controller.md` Task 10 Step 3: principle 15 names plan-layer's controller (`move.py`, `sync --tracker`) in a word-neutral swap, and `docs-and-decisions.md` gains one sentence saying a "changed X, so Y must change" rule is a co-change rule in `meta.controller.rules`, fired on a stage event. This matches plan-layer 0.19.0's CHANGELOG ("Rules on events", "One writer").

This plan **refers to** the source plans' tasks by number and does not copy them. It settles only what combining them changes: the version, the order of tasks on one branch, file collisions, the SKILL.md word budget, one set of runs, the release bar, model routing and the README entries. Where it says nothing, the source task applies as written.

**Tier b (internal).** The repository is public and other people install from it, but building this touches no live system and no user data. Push, PR and marketplace publish are a release and wait for the owner's word. Branch `engineering-method-0.5.0` (worktree `.worktrees/em-0.5.0`), cut from `main` at `87016f8`. One writer per worktree.

**Model that wrote this plan:** `claude-opus-5-5`. Written 26 Nov 2026 (`date -u`: Thu Nov 26 01:29 UTC).

## 1. Measured before planning (26 Nov 2026, worktree at `87016f8`)

Every figure below was read in this pass. Task I-0 re-reads them before building.

- **Unit suite:** `set -o pipefail; python3 -m unittest discover -s plugins/engineering-method/tests </dev/null 2>&1 | tail -3` → `Ran 73 tests … OK`, exit 0. EV's "0.4.0 had 71" is stale.
- **Version:** `plugins/engineering-method/.claude-plugin/plugin.json` → `0.4.0`; root `README.md` → `Current: 0.4.0.`
- **SKILL.md budget**, counted with `tests/test_skill_budget.py`'s own `split_skill()` and `stage_rows()`: body **2,198** of 2,200. Stage cells: plan 22, debug 12, build 22, review 20, test 20, deploy 22, merge 13, release 19, report 22 (limit 25).
- **What changed after 0.4.0's measured head.** `git diff --stat 969d99b 87016f8 -- plugins/engineering-method` (969d99b = the commit 0.4.0's "Eval results" name) touches only `CHANGELOG.md`, `README.md`, `COVERAGE.md`, two graders, `references/review-loop.md` and `references/root-cause-investigation.md`. So SKILL.md and every other reference are byte-identical to what 0.4.0's recorded results measured.
- **Routing of every planned prompt** (each prompt body extracted from the two plans, frontmatter stripped, piped to `scripts/method_hook.py --prompt` with a fresh `session_id` and a scratch `CLAUDE_PLUGIN_DATA`): the six EV cases, `verified-matches-plan` and `permission-profile-exploration-light` → `stage test`; `permission-profile-live` → `stage deploy`; `verified-near-miss-no-plan` → silent. All ten match what the source plans predicted.
- **Routing of the 35 existing cases** (same probe):

| Stage | Cases |
|---|---|
| test (4) | `eval-plan-as-dataset`, `owner-update-from-ledger`, `rc-07-trace-dropped-fact`, `test-report-shows-evidence` |
| debug (4) | `live-deploy-safeguards`, `rc-09-close-the-loop`, `rc-activation-loads-reference`, `state-claim-measured` |
| report (1) | `step-checklist-reprint` |
| deploy (1) | `rc-10-blind-brief` |
| merge (8) | `activation-without-trigger-words`, `enforce-not-instruct-headers`, `fix-fits-what-exists`, `provisioning-pre-launch-instance`, `push-guard-every-party`, `rc-01-pin-what-ran`, `rc-06-inventory`, `stage-change-activation` |
| release (2) | `deploy-helper-fault-triage`, `rc-08-label-and-fit` |
| plan (4) | `blocked-release-first`, `instruction-file-compression`, `settled-ruling-synonyms`, `supervise-lanes-cheap-tick` |
| build (2) | `declined-permission-stops`, `reviewer-different-model` |
| review (1) | `fix-loop-bounded` |
| silent (8) | `intent-over-literal`, `prototype-no-ceremony`, `rc-02-decision-record`, `rc-03-full-input`, `rc-04-objection`, `rc-05-diff`, `rc-near-miss-rename`, `zero-must-be-proven` |

  W's regression set (cases routed to test, deploy, merge or release) is **15** today, not the 9 it estimated. W also left out debug and report, which load `measurement-and-state-claims.md` (the file A changes): 5 more cases.
- **Anchors.** Every `old:` string and insertion point both plans rely on was checked against the 0.4.0 files, exactly and with whitespace normalised: EV Task 3 Steps 1, 2, 3, 4 (both headings), 4b (floor cell, test-first bullet, model-routing clause) and 6, the "Reading results" and "Cost plan before any run" headings; EV Task 4's principle 18 string; W Task 4's "State words" and "Labels" headings, the intro list "state words and labels" and the `test` cell; W Task 5's "Standing rules" / "Ask before mutating" row and the three §4 strings; (c)'s principle 15 string and the docs-and-decisions sentence. **All 23 occur exactly once. None moved.** One detail: the docs-and-decisions sentence ("…not another line in the instructions file (SKILL.md principle 7).") wraps across lines 95-96, so the Edit's `old_string` must include that line break. The tracker plan quotes it on one line.
- **A broken grep in W.** W Task 4 Step 4 (reused by Task 5 Step 4) passes `-e -- --since`. Under ugrep (this machine's `grep` is a shell function that calls ugrep) and under BSD `/usr/bin/grep`, `-e` takes `--` as the pattern and `--since` is then parsed as an unknown option. The command prints usage to stderr and **nothing to stdout**, which reads like "0 hits". Use `--regexp=--since`; it was checked under both greps and finds the planted line.
- **Contamination baseline** (the 0.4.0 lesson: a 6-gram check against every prompt, commit `827c8a7`; this release uses 5-grams, which is stricter). 5-word sequences shared between the instructions (SKILL.md and every reference) and the existing case prompts, frontmatter stripped: **1**, namely `zero-must-be-proven`'s "can I tell the team", which is a deliberate trigger phrase. Counting graders too gives 92 overlaps in 23 case/file pairs; graders share the rules' vocabulary by design, so they are reported but do not gate. The planned new text (EV Task 3, W Tasks 4-5, the two (c) lines) against the ten planned prompts: **0** shared 5-grams. Both plans' distinctive-string lists against that new text: 0 hits. Against the current files: `pytest` (on W's list) already appears in `references/live-system-changes.md:64` and `references/progress-ladder.md:42`. That is harmless, because `pytest` belongs to the guard case `permission-profile-exploration-light`, which is expected green on both versions; it is recorded so nobody is surprised later.
- **CLI:** `claude --version` → `2.1.332 (Claude Code)`.

## 2. Version and changelog

- **0.5.0 for everything.** W's "0.6.0" becomes 0.5.0 everywhere it appears: its Task 6 headings, version lines and commit messages, and the File structure line. 0.5.x is kept for fixes to 0.5.0.
- **One CHANGELOG entry**, `## 0.5.0 — <date -u at commit>`, in this order: evaluation method (EV's rules R1-R7, one paragraph each; it says the test-first bullet now records a red-on-head result instead of requiring green, which writes 0.4.0's recorded exception into the rule); "verified" measured against the plan (A); permission profiles per tier (B); controller pointers (c); the SKILL.md swaps with net words (2,198 → 2,197); the new unit test; the ten cases; the release ruling (section 5); eval results; spend.
- **COVERAGE.md:** two sections, the same shape as 0.4.0: `## Evaluation method (0.5.0)` (EV's rows) and `## Rules added in 0.5.0` (W Task 6's rows for A and B). Gap ids continue from **G44** (0.4.0's last is G43), in task order: EV's rules first, then A, then B. Guard rows and known-red rows are marked as 0.4.0 marks them.
- **Dropped:** EV Task 4 (principle 18, conditional on the owner's Q1). The owner has **not** said yes, so this plan leaves it out. If the owner later says yes, it fits (measured: 2,197 → 2,199) and ships as 0.5.1 with its own regression run.

## 3. Tasks, in order, with the files each one edits

One branch, serial, one writer. The only file more than one task edits is SKILL.md, and each of those tasks touches a different region: §3 (I-4), §4 (I-5) and §2 principle 15 (I-6). Each is measured with the budget test's counter before and after.

| # | Task | Source | Files edited (all under `plugins/engineering-method/` unless rooted) |
|---|---|---|---|
| I-0 | Preconditions, baselines and source re-reads, once | EV T0 Steps 3-4, W T0-EM Steps 3-6 (replaces EV T0 Steps 1-2 and W T0-EM Steps 1-2: no rebase, the base is `87016f8`) | none |
| I-R | Plan review of this file | section 9 | this plan (fixes only) |
| I-1 | All ten new cases and the snippet test, before any text | EV T1; W T1; W T2 | `evals/eval-score-code-first/`, `eval-pass-k-floor/`, `eval-metrics-report-only/`, `eval-judge-independent-calibrated/`, `eval-run-accounting/`, `eval-near-miss-unit-test/`, `verified-matches-plan/`, `verified-near-miss-no-plan/`, `permission-profile-live/`, `permission-profile-exploration-light/` (CREATE); `tests/test_permission_profiles.py` (CREATE, red) |
| I-2 | **One base run** on 0.4.0, then narrowing | EV T2 Steps 1-6, 8; W T3 | narrowed graders under the ten case folders |
| I-3 | Evaluation-method text | EV T3 | `references/behaviour-evals.md`, `references/model-routing-and-cost.md` |
| I-4 | A's text | W T4 | `references/measurement-and-state-claims.md`, `SKILL.md` §3 `test` cell |
| I-5 | B's text | W T5 | `references/permission-profiles.md` (CREATE), `references/live-system-changes.md` (one Standing rules row), `SKILL.md` §4 list |
| I-6 | The 0.4.1 edits | tracker plan T10 Step 3 | `SKILL.md` principle 15, `references/docs-and-decisions.md` (one sentence) |
| I-7 | Coverage, changelog, version, use cases | EV T6, W T6, section 8 | `evals/COVERAGE.md`, `CHANGELOG.md`, `.claude-plugin/plugin.json`, `README.md` (Use cases); root `.claude-plugin/marketplace.json`, root `README.md` |
| I-8 | **One head run** (the ten new cases) | EV T5 Steps 1, 3-4; W T7 Step 1 | case fixes only, if a judge or grader is shown wrong |
| I-9 | **One regression run** (the 35 existing cases) | EV T5 Step 2; W T7 Steps 2-4 | none |
| I-10 | Results into CHANGELOG and COVERAGE, full suites, identifier scan | EV T6 Step 2 (results), EV T7, W T7 Step 5 | `CHANGELOG.md`, `evals/COVERAGE.md` |
| I-11 | Whole-branch review and fix rounds | EV T8; W T11 Steps 3-5 (EM parts) | per findings |

What combining changes inside each task:

- **I-0.** Record the OK count (73 expected), the body word count (2,198) and the cells, and run the anchor check from section 1 (23 strings, each found once). Re-read every public page in EV "Vendor and baseline facts" and W "Measured facts" (Claude Code permissions, permission-modes, settings, settings-reference, plugin-evals; the Warp pages; the cited papers). Mark each fact confirmed, contradicted or changed, with its quote. Settle W's `disableAutoMode` key path. Record `claude --version` and which account the runs bill to (EV T2 Step 2, done once).
- **I-1.** Three commits, keeping the source messages (EV T1 Step 8; W T1 Step 5; W T2 Step 8). In every contamination grep, write `--since` as `--regexp=--since`, join wrapped lines (`tr '\n' ' ' | tr -s ' '`, the 0.4.0 form), and prove each grep can fire on the plan file. Routing was already measured (section 1); re-probe only a prompt that changed. Expected unit result: the new snippet tests ERROR and everything else passes (W T2 Step 6).
- **I-2.** One base worktree at `87016f8` with the ten case folders copied in (`diff -r` one of them). **One** calibration run: `eval-run-accounting`, cap $1, which also answers EV T2 Step 3's question about whether the hook fires in eval runs. Then the ten cases at 3 runs each, one command per case. Narrowing budget: EV's three predicted-green cases, up to two rounds each; W's `verified-matches-plan`, up to four rounds; `permission-profile-live`, up to two. Every round is base only and committed separately. A Fable 5.2 review of the narrowed graders closes the task (EV T2 Step 8; W T3 Step 3's labels). The regression base is **not** run here; it runs in I-9, paired with head.
- **I-3 to I-6** follow the source text as written, adjusted only where I-0 found a page changed. After each one: the unit suite, the body count, and the contamination checks from section 6. I-4's "snippet tests still red" holds until I-5.
- **I-6.** Swap in principle 15: `reconciled at every progress report (plan-layer: \`/plan-layer sync --tracker\`;` becomes `reconciled on events by plan-layer's controller (\`move.py\`, \`sync --tracker\`;` (9 → 9 words, measured). In `docs-and-decisions.md`, after "…(SKILL.md principle 7)." (lines 95-96, wrapped), add: `With plan-layer, a "changed X, so Y must change" rule is a co-change rule in \`meta.controller.rules\`, fired on a stage event.` Commit: `engineering-method: principle 15 and docs-and-decisions point at plan-layer's controller`.
- **I-7.** Sections 2 and 8 settle the headings and the use-case text. One commit: `engineering-method 0.5.0: coverage, changelog, version, use cases`.
- **I-10.** `git diff main --stat` lists only the files in the table above plus this plan and the EV plan. The identifier scan follows EV T7 Step 3. Commit: `engineering-method 0.5.0: measured eval results`.

## 4. SKILL.md word budget (body ≤ 2,200)

Measured by applying every swap to a scratch copy of the plugin and running the budget test's counter after each one. The full unit suite then passed on that copy (73 OK).

| Edit | Region | Δ words | Body after |
|---|---|---|---|
| start (`87016f8`) | | | 2,198 |
| I-4: `test` cell, W T4 Step 3 | §3 | 0 (cell 20 → 20) | 2,198 |
| I-5: `parallel-and-worktrees.md` gloss | §4 | −2 | 2,196 |
| I-5: `docs-and-decisions.md` gloss | §4 | −3 | 2,193 |
| I-5: add `permission-profiles.md` (settings per tier) | §4 | +4 | 2,197 |
| I-6: principle 15 controller swap | §2 | 0 | **2,197** |
| EV T4 (principle 18): **excluded**, no owner yes | §2 | (+2) | (2,199 if later approved) |

Every cell stays ≤ 25 words. `method_hook.py` is not edited, and no reference moves between stage rows.

## 5. Release bar (the same policy as the owner's 26 Nov 2026 ruling for 0.4.0, not a new one)

- **Deterministic checks gate:** the three plugins' unit suites, `claude plugin validate`, and the release gates (`validate`, `version-gate`, `payload-scan`) all pass.
- **Regression evals (the 35 existing cases) must hold:** no criterion's verdict (2 of 3 or better) drops from base to head. When a drop appears, pool both versions to 6 runs, compute a two-sided Fisher exact test, and read the answers behind it. A drop explained by reading and by the test (noise, or a judge error) is recorded with its p value, as `deploy-helper-fault-triage` was in 0.4.0. An unexplained drop stops the release and goes to the owner. Criteria already known red on 0.4.0 are not drops when they stay red.
- **New criteria (capability evals) are reported:** k of n on base and on head per criterion. One below 2 of 3 on head is recorded as **known red (capability)** in COVERAGE and the CHANGELOG, not held. The two near-miss guards (`eval-near-miss-unit-test`, `verified-near-miss-no-plan`) and `permission-profile-exploration-light` are read as regression evals: they must stay green on head.

## 6. Runs, cost and billing

**Billing line.** Evals run through `claude plugin eval` on the logged-in Claude subscription (I-0 confirms the account and records it). The runner's `costUsd` is a list-price **estimate** that already includes the judge calls; it is not plan usage and not a bill. **The owner's yes is required before the first run** (the calibration run in I-2).

**Flags on every command:** `--model opus --judge-model sonnet --ablation none -j 1 --runs 3 --threshold 0 --no-publish --trust-plugin --keep-temp --json <out>`. Each command's `--max-cost-usd` (its runs × that case's measured cost × 1.25) is written in the task before the command runs.

| Phase | Runs (max) |
|---|---|
| I-2 calibration (one, shared) | 1 |
| I-2 base: 10 new cases × 3 | 30 |
| I-2 narrowing, base only: EV ≤ 18, W ≤ 18 | ≤ 36 |
| I-8 head: 10 new cases × 3 | 30 |
| I-9 paired regression: the 20 cases routed to a stage whose reference changes (test, debug, report, deploy, merge, release), base and head, × 3 | 120 |
| I-9 smoke: the other 15 (plan, build, review, silent; `rc-03` with `--scaffold`), head × 1, compared with 0.4.0's recorded verdicts (valid because their loaded text is unchanged since 969d99b except SKILL.md's swaps) | 15 |
| Pooling and smoke escalation (a smoke fail on a criterion green on 0.4.0 → 3 runs on both versions) | ≤ 30 |
| I-11 reviewer re-run of one new case on head | 3 |
| **Total** | **≤ 265 (expected about 229)** |

At ~$0.26 a run (0.4.0's measured figure: $20.76 for 84 runs is $0.25), the estimate is **≤ ~$69, expected ~$60**. A session ceiling of **$70** is written before the first run; past it, stop and report.

**Deduplication.** As written, the two plans' separate estimates were 94 (EV, without Q1) + 138 (W) = 232 runs (~$60). Re-counted on today's measured routing, W alone becomes 174 (15 routed cases, not 9), and 204 once the 5 debug and report cases it left out are added; the two plans separately would then cost 298. Combined, this plan saves one calibration run, EV's 24 test-routed regression runs (inside I-9's 120), EV's separate pooling budget, and most of W's single-run whole-suite pass (41 → 15, since the cases already at 3 runs and the new cases are not run again).

**0.4.0 lessons that bind every run:**
- `rc-03-full-input` runs only with `--scaffold` (its `case.yaml` copies `resources/`). Read one kept trace to confirm the files arrived. A run with "No files found" is invalid, not a fail.
- `-j 1`. In-flight runs passed a cap under `-j 3`.
- Caps are written before each run, from each case's own measured cost. Never add the judge cost to `costUsd` a second time.
- Read the failing answers, and a sample of passing ones, **before** narrowing a criterion or calling a drop. Label each one: rule absent, judge error, or prompt/grader fault.
- **Fisher exact** (two-sided) on pooled runs whenever a drop appears; state the p value.
- **Contamination, 5-word check:** after I-3, I-4, I-5, I-6 and again in I-10, the count of 5-word sequences shared between the instructions and all case prompts (frontmatter stripped) must stay at the measured **1**, plus 0 hits from both plans' distinctive-string greps (`--regexp=` form, wrapped lines joined). Grader overlaps are listed, not gated.
- Runs that end on a usage or rate limit score 0 with no grader results. They are re-run, never counted as fails.

## 7. Model routing per task

| Task | Builder | Reviewer |
|---|---|---|
| I-0 | Opus (controller; the page re-reads are judgement) | — (findings go into I-R) |
| I-R | — | Fable 5.2, fresh, own worktree |
| I-1 cases | Opus (graders, contamination, routing) | Fable 5.2 |
| I-1 `test_permission_profiles.py` | Sonnet (the code is literal in W T2 Step 5) | Fable 5.2 |
| I-2 base run and narrowing | Opus (controller; reads the answers) | Fable 5.2 (the narrowed graders) |
| I-3 evaluation-method text | Opus (judgement text, adjusted to I-0 and I-2) | Fable 5.2 (re-reads each cited page) |
| I-4 A's text | Sonnet (the text is literal in W T4) | Fable 5.2 |
| I-5 B's text | Opus (every behaviour line is checked against the re-read pages) | Fable 5.2 (pastes each snippet into a scratch `.claude/settings.json`) |
| I-6 controller pointers | Sonnet (two literal edits) | Fable 5.2 |
| I-7 coverage, changelog, version, use cases | Sonnet (rows and text literal in EV T6, W T6 and section 8) | Fable 5.2 |
| I-8, I-9 runs | Opus (controller) | — |
| I-10 results | Opus (the results need reading) | Fable 5.2 |
| I-11 whole branch | — | Fable 5.2, fresh, blind brief, executes probes |

The eval judge is Sonnet. That differs from the Opus agent under test, the Opus implementers and the Fable reviewers. Every agent reports the model id it ran as. Each builder is capped at 60 tool calls per task; an agent past its cap is told to stop and report. Review rounds follow `review-loop.md` (five-round cap, re-reviews cover the delta only).

## 8. README "Use cases" entries (I-7, `plugins/engineering-method/README.md`)

Append in the section's existing form. None of these use a case's distinctive strings.

```markdown
- **You ask what graders a new eval case should have.** The agent puts a code check (a pattern over
  the reply, a tool called, a file created) wherever one can decide, keeps an LLM judge for what
  needs reading and says why code cannot decide it, and writes binary pass and fail conditions
  instead of a score to average. It pins the judge by name, on a different model from the one under
  test and the one that wrote the instructions, and calls the judge "uncalibrated, n = …" until
  enough of your own rulings back it.
- **A behaviour eval reads 2 of 3.** The agent reports k of n per criterion, holds a rule that must
  never break to every run (pass^k), and says how little three runs can prove. A run whose inputs
  never reached the agent is reported apart, as invalid. A new rule's case still red is recorded as
  known red; a drop on an existing case gets more runs and a reading of the answers, then goes to
  you.
- **You say "all tests pass, mark it verified".** On tier b or c the agent first compares the diff
  with the plan's steps and its out-of-scope list. It lists each mismatch with file and line: out of
  scope, a step with no change, or a change nobody asked for. It withholds "verified" until you rule
  on each one, and fixes nothing on its own. With no mismatch it says so with the counts and the
  command, for example `diff matches the plan: 5 steps, 4 out-of-scope lines checked`.
- **You ask for a project settings file for a live service.** The agent gives you the live profile
  from `references/permission-profiles.md` to paste into the committed `.claude/settings.json`: what
  must never run under deny, every command that can change the live system under ask, and bypass
  disabled. It explains that deny wins over any allow in any settings file, and that a Bash rule
  matches the command text, not the program, so a sandbox or a PreToolUse hook is the hard floor.
  It never edits your settings file itself.
```

The controller pointers (c) get no entry; plan-layer's README already carries those use cases.

## 9. Review of this plan (I-R, before I-1)

A fresh Fable 5.2 agent in its own worktree of `87016f8` gets this file, the two source plans and a blind brief (goal, paths, constraints). It must execute, not read: re-run the section 1 measurements (the suite, the body count, the routing of all 45 prompts, the 23 anchors, the `--since` grep under both greps, the 5-gram baseline); apply the section 4 swaps to a scratch copy and re-count; check that section 3's file map is the union of the source tasks' files and that no two tasks edit one region; recompute section 6's totals. It reports findings with file, line and the probe behind each, plus its model id. The controller reads any docs-only fix round from the diff.

## Out of scope

- Everything in the two source plans' "Out of scope" lists.
- EV Task 4 (principle 18), pending the owner's Q1.
- W lane PL (Tasks 0-PL, 8-10; shipped as plan-layer 0.20.0) and W Task 11 Steps 2 and 4's PL parts.
- Any change to `method_hook.py`, the stage map, the session brief or any trigger phrase.
- Re-opening 0.4.0's known-red results or its release ruling.
- Push, PR, tag or marketplace publish.

## Open questions (for the owner, each with a recommendation)

- **Q-1. EV's R5 against the 26 Nov ruling.** R5's first bullet says a judged score "does not block" a release. The 0.4.0 ruling splits evals: capability evals report, regression evals hold. Principle 18 (unchanged, since there is no Q1 yes) says an unexplained difference stops the release. *Recommendation:* in I-3, word R5's first bullet as that split (new-rule cases report; existing cases hold, and an unexplained drop goes to the owner). That writes down a ruling already made, removes the SKILL.md-versus-reference disagreement EV's Q1 warned about, and makes Q1 unnecessary. It edits reviewed text, so it needs the owner's yes; without one, EV's text ships as reviewed and the disagreement is stated in the CHANGELOG.
- **Q-2. Regression depth.** *Recommendation:* section 6 (20 routed cases paired at 3 runs, 15 others at 1 run against 0.4.0's record; ≤ 265 runs, ~$60-69). Alternative: all 35 paired at 3 runs (210 regression runs instead of 135, ≤ 340 in total, ~$88).
- **Q-3. The go for the runs:** the owner's yes on the billing line above, before I-2's calibration run.
