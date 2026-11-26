# engineering-method 0.5.1 ("hybrid") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the five behaviours that shipped as known-red capability evals in 0.5.0, plus the routing gap at the `test` stage. Each gets a small shipped script that computes the verdict and prints a fixed block. The agent runs it and pastes the block. Code graders score the block, and an `llm` grader stays only for what code cannot decide.

**Architecture:** Three stdlib Python scripts ship in the skill's own `scripts/` folder, which is the layout the skills docs document:
- `eval_stats.py`, with subcommands `floor`, `calibrate` and `runs`, covers behaviours 1, 2 and 3.
- `plan_conformance.py` covers behaviour 4.
- `permissions_check.py` covers behaviour 5.

How the parts fit:
- Each script reads fixed choices, file paths or stdin, and prints a versioned `KEY: value` block.
- Each script exits 0 whenever it computed a result, whatever the verdict: it reports and never gates. It exits 2 on bad input.
- The references tell the model when to run each script and to paste its block as printed.
- The five eval cases are edited in place:
  - `max_turns` rises to 16, and `Bash` is listed in `allowed_tools`.
  - The run itself grants Bash with `--allow-tools "Bash(python3 *)"`.
  - A `regex` grader on `target: trace` proves the script ran (its block header appears in the tool output; Task 0 measured that Bash output is in the trace). `tool_used` is not scored: it counts denied and failed calls too (Task 0, run 1). Other `regex` graders match the fixed lines in `last_message`.
  - `llm` graders are narrowed to the residual reading.

**Tech stack:** Python 3.10+ stdlib (`argparse`, `csv`, `json`, `math`, `re`, `statistics`, `fnmatch`), `unittest`, `claude plugin eval` (local CLI 2.1.332).

**Stakes tier: b.** This is a public library others install. TDD on every script, headers on every new definition, a reviewer from a different model that runs probes, all five CI checks green, and a no-regression gate on the cases the changed text can reach.

## Global constraints

- **Scope is locked** to the five behaviours (`eval-pass-k-floor` c1, `eval-judge-independent-calibrated` c2, `eval-run-accounting` c2, `verified-matches-plan` c4, `permission-profile-live` c1) and the test-stage routing gap. Nothing else.
- **No new eval cases.** The five existing cases are edited in place. One case's prompt changes what its criteria test (`eval-judge-independent-calibrated`: labels supplied). The CHANGELOG says c2 and c3 were redefined, not closed against the 0.5.0 wording. (Owner's ruling: edit the existing case, no new cases; raised as its own line.)
- **Python 3.9.** The sandboxed eval runs use `/usr/bin/python3` 3.9.6 (Task 0). Every new script and test runs on Python 3.9: no `match` statements, no runtime `X | Y` unions (`from __future__ import annotations` is fine), no 3.10+ stdlib calls. Each script task runs its tests with `/usr/bin/python3` too.
- **Eval commands** are prefixed `PATH=/usr/bin:/bin:/usr/sbin:/sbin` with `claude` called by its absolute path (read once with `command -v claude` before the prefix), so the session's `python3` is the system one outside home. They run against a **copy of the plugin outside the home folder** (the sandbox cannot read `~/Documents`, measured in Task 0; the eval uses the plugin folder in place).
- **Public repo:** no private names, product names, decision ids, tracker ids or links, or emails in any committed file. Say "the owner".
- **Budgets:**
  - SKILL.md body ≤ 2,200 words (now 2,197).
  - Stage cell ≤ 25 words (`CELL_WORD_LIMIT = 25`; the test cell has 20 now).
  - The hook's stage message ≤ 400 characters before truncation.
- **Code headers:** every new module and function carries the six labels `What:`, `Use when:`, `Inputs:`, `Output:`, `Side effects:`, `Role:` ("none" allowed). Untouched code gets none.
- **Exit codes, all scripts:** 0 = computed (any verdict); 2 = bad input, an `ERROR:` line on stderr and nothing on stdout. No exit 1.
- **Arguments** are fixed choices, file paths, or stdin text. A script never takes a verdict as an argument.
- **Script output must never print `disableBypassPermissionsMode`**, and prints `Bash(ssh` only when a supplied file contains it. The `permission-profile-exploration-light` guard is a case-insensitive `not_contains` on `last_message`.
- **No `claude plugin eval` without the owner's yes** on the session count in "Eval plan". Task 0's probe is gated the same way.
- **Do not push until the release task.** Every commit ends `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Vendor facts this plan rests on (read 26 Nov 2026, cited)

| Fact | Source | Status |
|---|---|---|
| Six grader types: `regex`, `tool_used`, `tool_order`, `file_exists`, `llm`, `baseline`; "There are no custom-code graders." | code.claude.com/docs/en/plugin-evals, "Choose and weight graders" | documented |
| `regex` `target`: `last_message` (default), `trace`, `files`, `{source: file, path}`, `mock_calls`; `match: not_contains` / `count:N`; only `flags: i` documented; JavaScript regex, no inline `(?i)` | plugin-evals, "Grader types", "What a grader can look at" | documented |
| `tool_used` `input_match` is a regex over the JSON-encoded tool input. The docs' own pattern: "assert the command ran with a `tool_used` grader whose `input_match` names the command" | plugin-evals, "Choose graders that give a stable signal" | documented |
| Bash is removed unless granted at run level with `--allow-tools`. The grant applies to every case in the run. A case's `allowed_tools` cannot widen it | plugin-evals, "Grant tools", "Trust the plugin directory" | documented |
| With Bash granted, commands run in the OS sandbox: writes confined to the workspace, "your home directory and Claude Code configuration are unreadable" | plugin-evals, "Shell grants need a sandbox" | documented. **Consequence: the plugin must be evaluated from a copy outside the home folder** (this checkout is under `~/Documents`) |
| `${CLAUDE_PLUGIN_ROOT}` / `${CLAUDE_SKILL_DIR}` are substituted in skill Markdown. They are not in the environment of Bash tool calls | skills, "Available string substitutions"; plugins-reference, "Where each variable resolves" | documented. **Measured (Task 0):** substituted in SKILL.md; a Read reference file gets the literal text. References therefore say "the skill's base directory" and never carry the variable |
| The documented bundled-script layout is `<skill>/scripts/x.py`, run as `${CLAUDE_SKILL_DIR}/scripts/x.py` | skills, "Bundled scripts in a scripts/ directory" | documented |
| Plugin `bin/` is on the Bash PATH while the plugin is enabled, but `bin/` blocks claude.ai/Cowork install | plugins-reference, "Standard layout" | documented; **measured not on PATH in eval runs** (`command not found`, Task 0) |
| `trace` = "the session as JSON, one message per line"; whether tool results are in it | plugin-evals | not stated; **measured yes** (Bash stdout and stderr are trace lines, Task 0) |
| `tool_used` counts every call, including permission-denied and failed ones | Task 0 run 1 ("Bash called 2x", one denied) | measured; so it is a hint, not proof the script ran |
| Sandboxed Bash cannot read under the home folder; `python3` on a PATH under home dies; `/usr/bin/python3` 3.9.6 runs | plugin-evals, "Shell grants need a sandbox"; Task 0 runs 1-2 (`PermissionError` on a file under `~/Documents`) | documented and measured |
| Default `max_turns` 10; hitting it is a run error | plugin-evals, prompt.md table | documented |
| A scaffold needs `case.yaml` (`schema_version: "1.1"`, `name`, `context.scaffold_script`) and `--scaffold` | plugin-evals, "Seed the workspace"; precedent `evals/rc-03-full-input` | documented, used |
| Permission order: "deny, then ask, then allow. The first match in that order determines the outcome". "If a tool is denied at any level, no other level can allow it". Lists merge across files | code.claude.com/docs/en/permissions, "Manage permissions", "Settings precedence"; settings, "Lists merge instead of overriding" | documented |
| Bash wildcards: `*` matches any text; a trailing ` *` that is the only wildcard also matches the bare command; the space is part of the rule; `:*` is a trailing-only alias of ` *`. Compound commands split on `&& \|\| ; \| \|& &` and newline: deny/ask apply if any part matches, allow needs every part; a dangling `&&`/`\|\|` is unparseable for allow | permissions, "Wildcard patterns", "Compound commands" | documented |
| `defaultMode` `bypassPermissions`/`auto` does not take effect from project or local settings | settings, "A value you set is ignored" | documented |

## Decisions

### Where the scripts live and how the agent calls them (one way)

- **Location:** `plugins/engineering-method/skills/engineering-method/scripts/`. This is the documented layout.
- **Call:**
  - The references write the call as `python3 <skill base directory>/scripts/<name>.py …`. The Skill tool prints "Base directory for this skill: …" when it loads, and every 0.5.0 trace shows that line.
  - SKILL.md's test cell names `scripts/plan_conformance.py` relative to the same base.
  - Nothing relies on `${…}` substitution inside a reference file: Task 0 measured that a Read reference gets the literal text.
  - The agent calls the script by its full path, never after `cd` (a `cd … &&` prefix is a compound command the `Bash(python3 *)` grant does not cover).
- **Alternative (one line):** `bin/` on PATH: rejected, it is not on PATH in eval runs (measured) and it blocks claude.ai/Cowork install.
- **Task 0** ran two probe sessions ($0.36 estimate) and confirmed this way works, given the operator conditions in Global constraints. A third probe (heredoc stdin, multi-line quoted argument) is pending; see Task 0.

### Per-behaviour decision table

| # | Tool (NEW) and input | Fixed output (key lines) | Code graders (NEW files) | Residual `llm` and why code cannot decide |
|---|---|---|---|---|
| 1 `eval-pass-k-floor` c1 | `eval_stats.py floor --name "<criterion>" --results <P/F/I per run>` (P pass, F fail, I invalid; repeatable pairs) | `RUNS: 2 of 3 passed; failed runs: 3; invalid runs: none` · `WILSON95: 0.21-0.94 …` · `PASS_K: pass^3 = 0.30 at the observed rate 0.67` · `PASS_K_LOW: pass^3 = 0.01 …` · `VERDICT: not-reliable (a never-break rule needs 3 of 3)` | `c1a-floor-tool-ran` regex trace `EVAL_STATS floor v1`; `c1b-pass-k-figure` regex `pass\^3 = 0\.30`; `c1c-floor-verdict` regex `VERDICT:\W{0,4}not-reliable` | `c1` narrowed: separates the majority from reliability and does not write the user's "reliable" line. Code cannot decide it because the answer quotes "reliable" while refusing it, and rebuttal versus echo is a reading. The pass^k figure moves to code, which also fixes the 0.5.0 known issue (grader stricter than the rule's Test line) |
| 2 `eval-judge-independent-calibrated` c2 | `eval_stats.py calibrate --labels -` (CSV on stdin: `answer_id,criterion,owner,judge`). The prompt now carries 9 labels (the user's two disagreements are on answers the user failed) | `LABELS: 9 (owner-pass 6, owner-fail 3)` · `TRUE_POSITIVE: judge passed 6 of 6 answers the owner passed` · `TRUE_NEGATIVE: judge failed 1 of 3 answers the owner failed` · `STATUS: uncalibrated, n = 9 (needs 30 owner-pass and 30 owner-fail; has 6 and 3)` | `c2a-calibrate-tool-ran` regex trace `EVAL_STATS calibrate v1`; `c2b-owner-pass-side` regex `judge passed 6 of 6 answers the owner passed`; `c2c-owner-fail-side` regex `judge failed 1 of 3 answers the owner failed` | `c2` narrowed: agreement is judged per side, and the answer does not present the overall 7 of 9 as the judge's accuracy. Code cannot decide it because the answer will quote 7 of 9 to rebut it |
| 3 `eval-run-accounting` c2 | `eval_stats.py runs eval-out/result.json --fixture parse-invoices=resources/`. A scaffold adds `eval-out/result.json` and kept traces | `COUNTS: valid 33, invalid 3, errored 0, no-trace 0` · `CASE: parse-invoices: invalid 3 of 3 (…)` · `RERUN: parse-invoices, after delivery is fixed; confirm with …` · `VERDICT: suite scored on 33 valid runs; 3 invalid reported apart, not counted as failed` | `c2a-runs-tool-ran` regex trace `EVAL_STATS runs v1`; `c2b-invalid-count` regex `invalid 3,`; `c2c-rerun-confirm` regex `RERUN: parse-invoices`; `c2d-not-counted-failed` regex `3 invalid reported apart, not counted as failed` | **Figures by code, stance by one narrowed judge.** `c2` narrowed: the report the answer recommends keeps the three runs out of the failed count and has them re-run. Code cannot decide it because the block can be pasted while the report beside it still counts the runs as failed, as the user asked (measured: such an answer passes every content grader). `c1` (cost estimate and cap) is unchanged and outside the gap |
| 4 `verified-matches-plan` c4 | `plan_conformance.py -` (the plan, diff-stat and hunks as text on stdin) | `CONFORMANCE: 2 mismatches, 1 check (…)` · `MISMATCH out-of-scope jobs/purge.py …` · `MISMATCH step-without-change README.md (step 3)` · `CHECK changed-existing report/cli.py --since … (no step names report/cli.py; …)` · `VERIFIED: withheld (owner rules on each: keep and add to the plan \| revert \| move to a later item \| do the step)` | `c4a-conformance-tool-ran` regex trace `PLAN_CONFORMANCE v1`; `c4b-withheld` regex `VERIFIED:\W{0,4}withheld`; `c4c-not-ok` regex `not_contains` `VERIFIED:\W{0,4}ok` | `c4` kept as written. It checks that the choices are laid out per mismatch, that the agent's own pick is not the path to verified, and that it reverts or fixes nothing itself. Code cannot decide it because whether prose overrides the tool's ruling with a self-chosen plan is a reading of stance (the exact 0.5.0 failure, 0/3) |
| 5 `permission-profile-live` c1 | `permissions_check.py --inline project='<json>' --command "<cmd>" …` (layers as `--inline SCOPE=JSON` or `--file SCOPE=PATH`) | Per command: `DECISION: deny` · `RULE: Bash(kubectl delete *) [deny] in project …` · `ORDER: deny > ask > allow; …` · `CROSS_FILE_PROBE: allow "…" added to user -> deny; added to local -> deny` · `LOOSENED_BY_OTHER_FILE: no (…)` | `c1a-checker-ran` regex trace `PERMISSIONS_CHECK v1`; `c1b-delete-deny-holds-across-files` regex: a `RULE:` line naming a `kubectl delete` deny, followed within the same block by `LOOSENED_BY_OTHER_FILE: no` (one pattern, Step 5.3) | `c1` narrowed: the file's allow is narrowed to read-only subcommands, and `kubectl delete` is not an exception inside allow. Code cannot decide it because the reply quotes the user's `Bash(kubectl *)` while explaining the change, so a `not_contains` would fail sound answers |

### Behaviour 4: where the gate lives

- **Decision: in engineering-method, as `plan_conformance.py`.** It reports, it does not block. `MISMATCH` is kept for the two facts code can settle: a changed file under an out-of-scope path, and a step-named file absent from the diff. A changed existing definition is a `CHECK` line (the model judges whether a step covers it). A `CHECK` withholds "verified" only when no step names its file, so an ordinary diff that does what its plan says is not withheld (review probe: two false mismatches before this change).
  - The case has no `plan.json`, and the eval loads only the plugin under test, so a plan-layer gate could not be reached or scored.
  - The script works with or without plan-layer.
  - Its last line carries the owner-rules wording into context even when no reference was Read, which was the routing gap.
- **Parked:** the plan-layer `move.py` gate (see Out of scope).
- **Routing fix:** two changes. The prototype measured the suite green on a copy (`Ran 79 tests … OK`, body 2,198, cell 21 words, hook message 353 characters; the reviewer measured 365 with Step 4.4's final text).
  - SKILL.md test cell: `diff vs plan steps, out-of-scope;` becomes `plan: run scripts/plan_conformance.py; owner rules mismatches;`. Apply it only if `test_skill_budget` passes; if not, ship the hook note alone and say so in the CHANGELOG.
  - Test-stage `note` in `method_hook.STAGES`: the text in Step 4.4 (365 characters measured by the reviewer, limit 400).
- The 0.5.0 traces show **no UserPromptSubmit event**, so the hook may not fire in eval runs (hypothesis). The cell is the route proven to load: the Skill call happened 3 of 3.

### Base comparability

- Every edited case gets a **fresh base run on 0.5.0**:
  - The base checkout is `fddb809` (`git worktree add --detach <scratch>/em-base-051 fddb809`) with the five 0.5.1 case folders copied over its `evals/`.
  - Same flags as head, same `--allow-tools`.
  - Base has no scripts, so every new code grader is decided by construction on base (the script-ran and content graders red, `c4c` green). The base-versus-head comparison is read only on the `llm` graders and the unchanged graders. Case means are not compared across versions for these five cases.
- Head runs on 0.5.1 from a scratch checkout of the branch head.
- Regression cases whose text and graders are unchanged reuse today's 0.5.0 head results as base. Measured: `git diff --stat 92d8696 fddb809 -- plugins/engineering-method` touches only CHANGELOG, README and COVERAGE, so the skill text is identical.

## Fit with what exists

- **Exists:**
  - `behaviour-evals.md` "Scoring: code first, a judge only where code cannot decide", "Repeated runs", "Judges", and its run-accounting bullet.
  - `measurement-and-state-claims.md` "Verified is measured against the plan".
  - `permission-profiles.md` "Across files, deny wins".
  - `method_hook.STAGES` with an optional per-stage `note` (debug has one).
  - `regex` graders (4) and `tool_used` graders (52) in the suite.
  - A scaffold precedent (`rc-03-full-input`).
  - **Absent:** any script the agent runs, any code that computes pass^k, calibration splits, run validity, plan conformance or settings precedence.
- **Extends:** each reference rule gains one sentence: "run X, paste its block as printed". The hook gains a test-stage note. The test cell swaps 5 words for 6. The five cases gain graders and keep their prompts (two gain fixture input). The narrowest change sits where the property must hold, in the rule's own reference.
- **Unlocks:**
  - Any later rule whose verdict is computable ships as tool + fixed block + code grader. Graders then match stable tool text, not paraphrase.
  - The same scripts serve real users outside evals (an actual eval report, an actual plan check, an actual settings file).
  - `runs` makes "invalid" a third outcome everywhere k of n is reported.
- **Goals:**
  - *As much as possible deterministic:* all figures and verdicts are computed by code and graded by code. Behaviour 3's figures need no judge; one narrowed judge reads its stance.
  - *Judge only for what code cannot decide:* five narrowed or kept `llm` graders, each with its reason in its header.
  - *Live today:* tasks sized for parallel lanes, one gated probe, one eval batch, then the release steps.
  - *Scope locked:* see Out of scope.

### EXTENDS / NEW per mechanism

| Mechanism | EXTENDS / NEW |
|---|---|
| `skills/engineering-method/scripts/eval_stats.py` | NEW (nothing computes these figures) |
| `skills/engineering-method/scripts/plan_conformance.py` | NEW (ported from the research prototype) |
| `skills/engineering-method/scripts/permissions_check.py` | NEW |
| `tests/test_eval_stats.py`, `test_plan_conformance.py`, `test_permissions_check.py` | NEW, in the existing test layout |
| `tests/test_script_headers.py` | NEW: the header check for the three scripts (principle 7: a missed rule gets a check) |
| `tests/test_hybrid_graders.py` | NEW: proves each new regex grader passes on the tool's real output and fails on a prose-only answer (a zero proven able to be non-zero) |
| `references/behaviour-evals.md` (3 bullets), `measurement-and-state-claims.md` (step 1), `permission-profiles.md` (1 bullet) | EXTENDS |
| SKILL.md §3 test cell | EXTENDS |
| `scripts/method_hook.py` STAGES test `note` | EXTENDS (debug-note precedent) |
| `tests/test_skill_budget.py`, `tests/test_method_hook.py` | EXTENDS (one assertion each) |
| Five case folders: frontmatter, graders, two prompt edits, one scaffold | EXTENDS |

## Out of scope

- **The history-mode release scan.** It belongs to a separate toolkit story.
- **The plan-layer `move.py` gate** that refuses `verified` while mismatches stand. The eval cannot reach it, it is a second plugin release, and nothing measured needs it yet.
- **A blocking Stop hook for plan conformance.** It is new enforcement on users' machines; plan-layer already runs a Stop gate; it needs the owner's yes.
- **A general saved-workflow or command library.** It would be a new artifact type; skills and slash commands already fill that role.
- **MCP servers for the tools.** A script printing a fixed block gives the same property.
- **Any other known-red or existing case**, including converting the `verified-matches-plan` c1-c3 guards or `permission-profile-live` c2-c4 to code, and adding a Bash guard to `verified-near-miss-no-plan`.
- **New eval cases beyond these five.**
- **Refactors** of existing code or references.
- **Other plugins' features.**
- **Cost and cap lines in `eval_stats.py runs`.** `eval-run-accounting` c1 is not in the gap.
- **Deferred to a later release** (from the plan review): a Bash `max: 0` grader on the two near-miss guards; `plan_conformance.py` handling of binary and renamed files in `--stat` and Markdown table rows that parse as stat lines (handed to the Task 6 reviewer as adversarial inputs); whether the UserPromptSubmit hook fires in eval runs; why `permission-profile-exploration-light` costs about four times the other cases; `rc-*` cases that read `measurement-and-state-claims.md` at the debug stage (add one to regression only if 7d is unused).
- **In `permissions_check.py`:** wrappers (`timeout`, `nice` …), env-assignment prefixes, nested subshell parsing, redirections, the built-in read-only command set, hooks and mods. The script prints them as `NOTES: not modelled …` and never guesses.

---

## Task list and lanes

| Task | Files | Depends on | Lane |
|---|---|---|---|
| 0. Probe + validate check | scratchpad only | runs 1-2 done; run 3 pending | serial, first |
| 1. `eval_stats.py` (floor, calibrate, runs) | `skills/engineering-method/scripts/eval_stats.py`, `tests/test_eval_stats.py` | none | **A** (parallel) |
| 2. `plan_conformance.py` | `skills/engineering-method/scripts/plan_conformance.py`, `tests/test_plan_conformance.py` | none | **B** (parallel) |
| 3. `permissions_check.py` | `skills/engineering-method/scripts/permissions_check.py`, `tests/test_permissions_check.py` | none | **C** (parallel) |
| 4. Routing + references + header check | `SKILL.md`, `scripts/method_hook.py`, 3 references, `tests/test_skill_budget.py`, `tests/test_method_hook.py`, `tests/test_script_headers.py` | 1-3 merged; Task 0 run 3 (call forms in Step 4.5) | **D** (parallel with E) |
| 5. Eval cases + grader proofs | `evals/{eval-pass-k-floor,eval-judge-independent-calibrated,eval-run-accounting,verified-matches-plan,permission-profile-live}/**`, `tests/test_hybrid_graders.py`, `tests/fixtures/hybrid/*` | 1-3 merged; Task 0 result | **E** (parallel with D) |
| 6. Whole-branch review | read-only | 4, 5 merged | serial |
| 7. Evals (gated) | scratchpad only | 6; owner's yes | serial |
| 8. Release | versions, CHANGELOG, COVERAGE, README | 7 | serial |

- **Lanes:** A, B and C touch disjoint files. Each runs in its own worktree cut from `engineering-method-0.5.1-hybrid`, one writer each. Merge order is A → B → C; the merges cannot conflict.
- D and E start after C merges. They touch disjoint files (D: skills, hook and three tests; E: `evals/` plus one new test and its fixtures). Merge D → E.
- Builders: Opus. Reviewer for each task and the whole branch: a different and at least as strong model (Fable 5.2). It runs probes and reports the model id it ran as.
- Implementers run their own test file only (with `python3` and `/usr/bin/python3`). The controller runs the full suite after each merge.

---

### Task 0: Probe the eval sandbox (runs 1-2 DONE; run 3 PENDING)

Done by a probe agent on 26 Nov 2026, 15:55-15:58 UTC, Claude Code 2.1.332. Two sessions, $0.14 + $0.22 (list-price estimates), subscription billing. Record: `<scratch>/probe0/probe-report.md`, `command-log.md`, `out/` and `out2/result.json`.

- [x] **Step 0.1 (free):** `claude plugin validate --strict` with a `.py` under `skills/engineering-method/scripts/` printed "Validation passed", exit 0. The Task 6 reviewer repeated it on the three real scripts with the same result.
- [x] **Step 0.2-0.4 (runs 1 and 2):** a throwaway probe plugin under the scratchpad, one case, `--runs 1`, `--allow-tools "Bash(python3 *)" "Bash(probe-bin *)"`. Run 2 added `PATH=/usr/bin:/bin:/usr/sbin:/sbin` and two reads of a file under `~/Documents`.

| Question | Measured answer | Consequence for this plan |
|---|---|---|
| `${CLAUDE_SKILL_DIR}` in SKILL.md | substituted, to the plugin's own folder (used in place) | the SKILL.md test cell may use it; the relative `scripts/…` form also resolves |
| The printed base-directory path | resolves (`PROBE-OUT-C-…`) | the references' call form stands |
| `${CLAUDE_SKILL_DIR}` in a Read reference | **literal** | references say "the skill's base directory", never the variable |
| `bin/` on PATH | **no** (`command not found`) | F1 is out |
| `python3` on a PATH under home | dies (`Failed to import encodings module`) | the eval command prefix in Global constraints |
| `/usr/bin/python3` | runs, 3.9.6, with two harmless `xcrun_db` stderr lines | the Python 3.9 constraint |
| Sandboxed read under `~/Documents` | **denied** (`PermissionError`) | evals run on a copy outside home |
| Bash output in `trace` | **yes**, stdout and stderr | the "script ran" graders are `regex` on `target: trace` |
| `tool_used` | counts denied and failed calls | not scored; a hint only |
| `last_message` paste | verbatim in run 2 | the content graders stand; F3 not needed so far |
| Turns | 6 and 10 of 12 (6 Bash calls in run 2) | `max_turns: 16` for the five target cases; read each run's `error`, not `turns` alone, since 0.5.0 showed `turns: 7` against `max_turns: 6` with no error |

- [ ] **Step 0.5 (run 3, PENDING, run by another agent):** settles the two call shapes four of the five cases depend on. Probe step E is `python3 <base>/scripts/probe.py E <<'EOF'` plus two lines plus `EOF`, with probe.py also printing `stdin_lines=%d`. Probe step F is `python3 <base>/scripts/probe.py F '{` newline `"a": 1}'`. Graders `heredoc.md` (`PROBE-OUT-E-[0-9a-f]{8}`) and `multiline.md` (`PROBE-OUT-F-`), both `target: trace`.

  **RESULT: (placeholder, the controller fills this in from the run-3 report before Task 4 and Task 5 start)**

  **Decision rule:**
  - **E passes:** `plan_conformance.py -` and `calibrate --labels -` take heredoc stdin as written in Step 4.5.
  - **E fails:** those two cases get a scaffold that places the text as a file (rc-03 pattern). The scripts already take a path (`plan_conformance.py <path>`, `--labels <path>`), and Step 4.5 says "pass a file path".
  - **F passes:** `permissions_check.py --inline project='<json>'` stands.
  - **F fails:** `permission-profile-live` gets a scaffold with the draft settings file, and the call is `--file project=<scaffolded path>`.

**Fallbacks still on file:**
- **F2 (the agent cannot run python3 at all):** not the case (run 2).
- **F3 (the block is paraphrased in `last_message`):** each script gains `--out PATH`, and the content graders target `{source: file, path: em-verdict.txt}`. Use it only if the 7a smoke shows paraphrase. Prefer a `target: trace` pattern on the tool's own line first: it needs no flag and keeps files out of users' repos.

---

### Task 1 (lane A): `eval_stats.py` (floor, calibrate, runs)

**Files:**
- Create: `plugins/engineering-method/skills/engineering-method/scripts/eval_stats.py`
- Test: `plugins/engineering-method/tests/test_eval_stats.py`

**Interfaces:**
- Produces:
  - CLI `eval_stats.py floor --name N --results LETTERS [--name … --results …]`
  - CLI `eval_stats.py calibrate --labels PATH|-`
  - CLI `eval_stats.py runs RESULT_JSON [--fixture CASE=PREFIX …]`
  - Block header `EVAL_STATS <cmd> v1`, footer `EVAL_STATS end`
  - Functions `wilson(k: int, n: int) -> tuple[float, float]`, `pass_k(k: int, n: int) -> float`, `floor_block(name: str, results: str) -> list[str]`, `calibrate_blocks(rows: list[dict]) -> list[str]`, `runs_block(path: str, fixtures: dict[str, str]) -> list[str]`
  - Task 5 consumes these exact line texts.

- [ ] **Step 1.1: Write the failing tests** (`tests/test_eval_stats.py`):

```python
"""Tests for skills/engineering-method/scripts/eval_stats.py.

What: runs the script as a subprocess on fixed inputs and pins its blocks byte for byte.
Use when: running the plugin's normal suite (python3 -m unittest discover tests).
Inputs: inline fixtures and temp files. Output: unittest results.
Side effects: creates and removes temporary directories.
Role: keeps the eval figures computed by code and pinned, so a reference and its graders cannot drift.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "skills", "engineering-method", "scripts", "eval_stats.py")


def run(*args, stdin=None):
    p = subprocess.run([sys.executable, SCRIPT, *args], input=stdin, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def load():
    spec = importlib.util.spec_from_file_location("eval_stats", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Floor(unittest.TestCase):
    def test_two_of_three_golden(self):
        code, out, _ = run("floor", "--name", "never quotes a refund amount", "--results", "PPF")
        self.assertEqual(code, 0)
        self.assertEqual(out, "\n".join([
            "EVAL_STATS floor v1",
            "CRITERION: never quotes a refund amount",
            "RUNS: 2 of 3 passed; failed runs: 3; invalid runs: none",
            "WILSON95: 0.21-0.94 (true per-run rate, 2 of 3)",
            "PASS_K: pass^3 = 0.30 at the observed rate 0.67",
            "PASS_K_LOW: pass^3 = 0.01 at the interval's lower bound 0.21",
            "VERDICT: not-reliable (a never-break rule needs 3 of 3)",
            "EVAL_STATS end", ""]))

    def test_three_of_three_is_reliable_on_this_sample_only(self):
        _, out, _ = run("floor", "--name", "x", "--results", "PPP")
        self.assertIn("PASS_K_LOW: pass^3 = 0.08 at the interval's lower bound 0.44", out)
        self.assertIn("VERDICT: reliable on this sample (3 of 3; rates below 0.44 not ruled out)", out)

    def test_zero_of_three(self):
        _, out, _ = run("floor", "--name", "x", "--results", "FFF")
        self.assertIn("RUNS: 0 of 3 passed; failed runs: 1, 2, 3; invalid runs: none", out)
        self.assertIn("WILSON95: 0.00-0.56", out)
        self.assertIn("PASS_K: pass^3 = 0.00", out)

    def test_invalid_runs_are_excluded_and_shown(self):
        _, out, _ = run("floor", "--name", "x", "--results", "PPIF")
        self.assertIn("RUNS: 2 of 3 passed; failed runs: 4; invalid runs: 3 (not counted)", out)
        self.assertIn("pass^3 = 0.30", out)

    def test_all_invalid_reports_no_figure(self):
        code, out, _ = run("floor", "--name", "x", "--results", "II")
        self.assertEqual(code, 0)
        self.assertIn("WILSON95: n/a (0 valid runs)", out)
        self.assertIn("VERDICT: no valid runs (re-run after delivery is confirmed)", out)

    def test_exponent_follows_n(self):
        _, out, _ = run("floor", "--name", "x", "--results", "PPPPPF")
        self.assertIn("PASS_K: pass^6 = 0.33 at the observed rate 0.83", out)

    def test_lower_case_and_two_pairs(self):
        _, out, _ = run("floor", "--name", "a", "--results", "ppf", "--name", "b", "--results", "PPP")
        self.assertEqual(out.count("EVAL_STATS floor v1"), 2)
        self.assertLess(out.index("CRITERION: a"), out.index("CRITERION: b"))

    def test_pass_k_from_the_fraction(self):
        self.assertAlmostEqual(load().pass_k(2, 3), (2 / 3) ** 3)

    def test_wilson_values(self):
        lo, hi = load().wilson(2, 3)
        self.assertEqual((round(lo, 2), round(hi, 2)), (0.21, 0.94))
        self.assertEqual(tuple(round(x, 2) for x in load().wilson(1, 1)), (0.21, 1.0))

    def test_bad_inputs_exit_2_with_empty_stdout(self):
        for args in (["--name", "x", "--results", ""], ["--name", "x", "--results", "PPX"],
                     ["--name", "x"], ["--results", "PP"], ["--name", "a", "--name", "b", "--results", "P"]):
            code, out, err = run("floor", *args)
            self.assertEqual((code, out), (2, ""), args)
            self.assertIn("ERROR:", err)


LABELS = "answer_id,criterion,owner,judge\n" + "\n".join(
    ["a%d,flags decisions that have no owner,pass,pass" % i for i in range(1, 7)]
    + ["a7,flags decisions that have no owner,fail,fail",
       "a8,flags decisions that have no owner,fail,pass",
       "a9,flags decisions that have no owner,fail,pass"]) + "\n"


class Calibrate(unittest.TestCase):
    def test_nine_labels_golden(self):
        code, out, _ = run("calibrate", "--labels", "-", stdin=LABELS)
        self.assertEqual(code, 0)
        self.assertEqual(out, "\n".join([
            "EVAL_STATS calibrate v1",
            "CRITERION: flags decisions that have no owner",
            "LABELS: 9 (owner-pass 6, owner-fail 3)",
            "TRUE_POSITIVE: judge passed 6 of 6 answers the owner passed",
            "TRUE_NEGATIVE: judge failed 1 of 3 answers the owner failed",
            "STATUS: uncalibrated, n = 9 (needs 30 owner-pass and 30 owner-fail; has 6 and 3)",
            "EVAL_STATS end", ""]))

    def test_calibrated_prints_rates(self):
        rows = ["answer_id,criterion,owner,judge"]
        rows += ["p%d,c,pass,%s" % (i, "pass" if i < 28 else "fail") for i in range(30)]
        rows += ["f%d,c,fail,%s" % (i, "fail" if i < 27 else "pass") for i in range(30)]
        _, out, _ = run("calibrate", "--labels", "-", stdin="\n".join(rows) + "\n")
        self.assertIn("TRUE_POSITIVE: 0.93 (28 of 30, Wilson95 0.79-0.98)", out)
        self.assertIn("TRUE_NEGATIVE: 0.90 (27 of 30, Wilson95 0.74-0.97)", out)
        self.assertIn("STATUS: calibrated", out)

    def test_no_rate_below_thirty_a_side(self):
        rows = ["answer_id,criterion,owner,judge"] + ["p%d,c,pass,pass" % i for i in range(30)] \
            + ["f%d,c,fail,fail" % i for i in range(29)]
        _, out, _ = run("calibrate", "--labels", "-", stdin="\n".join(rows) + "\n")
        self.assertIn("STATUS: uncalibrated, n = 59", out)
        for line in out.splitlines():
            if line.startswith("TRUE_NEGATIVE"):
                self.assertNotRegex(line, r"\b0\.\d\d\b")

    def test_side_with_no_labels_is_not_measured(self):
        rows = ["answer_id,criterion,owner,judge"] + ["p%d,c,pass,pass" % i for i in range(12)]
        _, out, _ = run("calibrate", "--labels", "-", stdin="\n".join(rows) + "\n")
        self.assertIn("TRUE_NEGATIVE: not measured (0 answers the owner failed)", out)
        self.assertIn("has 12 and 0; true negative rate unmeasured)", out)

    def test_header_only_is_n_zero(self):
        code, out, _ = run("calibrate", "--labels", "-", stdin="answer_id,criterion,owner,judge\n")
        self.assertEqual(code, 0)
        self.assertIn("CRITERION: (none labelled)", out)
        self.assertIn("STATUS: uncalibrated, n = 0", out)

    def test_criteria_sorted_and_separate(self):
        rows = "answer_id,criterion,owner,judge\n1,b,pass,pass\n2,a,fail,fail\n3,b,fail,pass\n"
        _, out, _ = run("calibrate", "--labels", "-", stdin=rows)
        self.assertLess(out.index("CRITERION: a"), out.index("CRITERION: b"))

    def test_file_and_stdin_agree(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
            fh.write(LABELS)
        try:
            self.assertEqual(run("calibrate", "--labels", fh.name)[1],
                             run("calibrate", "--labels", "-", stdin=LABELS)[1])
        finally:
            os.unlink(fh.name)

    def test_bad_labels_exit_2(self):
        for text in ("", "answer_id,criterion,owner\n1,c,pass\n",
                     "answer_id,criterion,owner,judge\n1,c,maybe,pass\n",
                     "answer_id,criterion,owner,judge\n1,c,pass,pass\n1,c,fail,pass\n"):
            code, out, err = run("calibrate", "--labels", "-", stdin=text)
            self.assertEqual((code, out), (2, ""), text)
        self.assertEqual(run("calibrate", "--labels", "/nonexistent.csv")[0], 2)

    def test_values_normalised(self):
        code, out, _ = run("calibrate", "--labels", "-",
                           stdin="answer_id,criterion,owner,judge\n1,c, PASS ,Pass\n")
        self.assertEqual(code, 0)
        self.assertIn("judge passed 1 of 1", out)


def trace_lines(tool, inp, result, is_error=False):
    """Two stream-json lines: an assistant tool_use and the user tool_result (shape pinned in Step 1.5)."""
    return [json.dumps({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t1", "name": tool, "input": inp}]}}),
            json.dumps({"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": result, "is_error": is_error}]}})]


def write_result(d, cases):
    """cases: {name: [(score, error, trace_lines or None), ...]}. Writes result.json + traces/; returns its path."""
    os.makedirs(os.path.join(d, "traces"), exist_ok=True)
    out = {"schemaVersion": 1, "partial": False, "cases": []}
    for name, runs in cases.items():
        arm = []
        for i, (score, error, lines) in enumerate(runs, 1):
            tp = None
            if lines is not None:
                tp = "traces/%s-%d.jsonl" % (name, i)
                with open(os.path.join(d, tp), "w") as fh:
                    fh.write("\n".join(lines) + "\n")
            arm.append({"score": score, "passed": score == 1, "error": error, "tracePath": tp,
                        "graders": [{"name": "c1", "passed": score == 1}]})
        out["cases"].append({"name": name, "arms": {"with": arm}})
    path = os.path.join(d, "result.json")
    with open(path, "w") as fh:
        json.dump(out, fh)
    return path


class Runs(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d)

    def test_undelivered_fixture_is_invalid(self):
        miss = trace_lines("Glob", {"pattern": "resources/**"}, "No files found")
        ok = trace_lines("Read", {"file_path": "x.py"}, "1 line")
        p = write_result(self.d, {"parse-invoices": [(0, None, miss)] * 3, "other": [(1, None, ok)] * 3})
        code, out, _ = run("runs", p, "--fixture", "parse-invoices=resources/")
        self.assertEqual(code, 0)
        self.assertIn("COUNTS: valid 3, invalid 3, errored 0, no-trace 0", out)
        self.assertIn("CASE: parse-invoices: invalid 3 of 3 (no tool result under resources/ "
                      "returned content in the kept trace)", out)
        self.assertIn("RERUN: parse-invoices, after delivery is fixed; confirm with "
                      "eval_stats.py runs <new result.json> --fixture parse-invoices=resources/", out)
        self.assertIn("VERDICT: suite scored on 3 valid runs; 3 invalid reported apart, not counted as failed", out)

    def test_delivered_fixture_is_valid(self):
        hit = trace_lines("Read", {"file_path": "resources/inv1.pdf"}, "%PDF-1.4 ...")
        p = write_result(self.d, {"parse-invoices": [(1, None, hit)] * 3})
        _, out, _ = run("runs", p, "--fixture", "parse-invoices=resources/")
        self.assertIn("CASE: parse-invoices: valid 3 of 3; delivery confirmed in 3 of 3 kept traces; "
                      "graders over valid runs: c1 3 of 3", out)
        self.assertNotIn("RERUN:", out)

    def test_error_result_is_not_delivery(self):
        bad = trace_lines("Read", {"file_path": "resources/a.pdf"}, "File does not exist.", is_error=True)
        p = write_result(self.d, {"c": [(0, None, bad)]})
        self.assertIn("invalid 1 of 1", run("runs", p, "--fixture", "c=resources/")[1])

    def test_missing_trace_and_errored(self):
        ok = trace_lines("Read", {"file_path": "x"}, "y")
        p = write_result(self.d, {"c": [(1, None, None), (0, "timeout", ok), (1, None, ok)]})
        _, out, _ = run("runs", p)
        self.assertIn("COUNTS: valid 1, invalid 0, errored 1, no-trace 1", out)

    def test_signal_without_fixture_is_a_fact_not_a_verdict(self):
        miss = trace_lines("Glob", {"pattern": "resources/**"}, "No files found")
        p = write_result(self.d, {"c": [(0, None, miss)]})
        _, out, _ = run("runs", p)
        self.assertIn('SIGNAL: c run 1: Glob returned "No files found"', out)
        self.assertIn("COUNTS: valid 1, invalid 0", out)
        self.assertIn("DELIVERY: not checked for 1 case (no --fixture given)", out)
        self.assertIn("VERDICT: suite scored on 1 valid runs; 0 invalid reported apart, not counted as failed "
                      "(delivery not checked for 1 case)", out)

    def test_bad_inputs_exit_2(self):
        p = write_result(self.d, {"c": [(1, None, trace_lines("Read", {"file_path": "x"}, "y"))]})
        self.assertEqual(run("runs", p, "--fixture", "nosuch=resources/")[0], 2)
        self.assertEqual(run("runs", p, "--fixture", "no-equals-sign")[0], 2)
        for broken in ({"schemaVersion": 2, "cases": []}, {"schemaVersion": 1},
                       {"schemaVersion": 1, "cases": []},
                       {"schemaVersion": 1, "cases": [{"name": "c", "arms": {"with": [{"score": 1}]}}]}):
            bp = os.path.join(self.d, "b.json")
            with open(bp, "w") as fh:
                json.dump(broken, fh)
            code, out, err = run("runs", bp)
            self.assertEqual((code, out), (2, ""), broken)
        with open(os.path.join(self.d, "traces", "c-1.jsonl"), "w") as fh:
            fh.write("{not json\n")
        self.assertEqual(run("runs", p)[0], 2)

    def test_partial_is_shown(self):
        p = write_result(self.d, {"c": [(1, None, trace_lines("Read", {"file_path": "x"}, "y"))]})
        with open(p) as fh:
            data = json.load(fh)
        data["partial"] = True
        with open(p, "w") as fh:
            json.dump(data, fh)
        self.assertIn("partial true", run("runs", p)[1])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 1.2: Run, expect red.**

```bash
cd plugins/engineering-method && set -o pipefail && python3 -m unittest tests.test_eval_stats -v 2>&1 | tail -5
/usr/bin/python3 -m unittest tests.test_eval_stats 2>&1 | tail -3   # Python 3.9, as the eval sandbox runs it
```
Expected: errors (the script file does not exist), `FAILED`.

- [ ] **Step 1.3: Implement** `skills/engineering-method/scripts/eval_stats.py`:

```python
#!/usr/bin/env python3
"""Compute the figures a behaviour-eval report needs, as fixed blocks to paste.

What: three subcommands. floor: k of n, a Wilson 95% interval, pass^n and a reliable /
not-reliable verdict for a never-break criterion (runs marked I are invalid and not counted).
calibrate: a judge's agreement with the owner's rulings, split into answers the owner passed
and answers the owner failed; rates only at 30 labels a side or more. runs: classify every run
in a claude plugin eval result.json as valid, invalid (a case's fixture input never reached
the agent, read from the kept trace), errored or no-trace.
Use when: writing an eval report (references/behaviour-evals.md); paste the block as printed.
Inputs: argv; calibrate reads a CSV path or "-" (stdin); runs reads a result.json and the
trace files it points to.
Output: an "EVAL_STATS <cmd> v1" ... "EVAL_STATS end" block on stdout. Exit 0 whenever it
computed (any verdict: it reports, it never gates); exit 2 on bad input, "ERROR: ..." on
stderr and nothing on stdout.
Side effects: none (reads files only, no network).
Role: computes facts so the model relays them instead of working them out by hand.
"""
import argparse
import csv
import io
import json
import math
import os
import sys
from statistics import NormalDist

Z = NormalDist().inv_cdf(0.975)
MIN_PER_SIDE = 30
EMPTY_RESULTS = ("no files found", "does not exist", "no such file", "not found")


class BadInput(Exception):
    """What: an input the script will not compute on. Use when: any parse or check fails.
    Inputs: message. Output: exception. Side effects: none. Role: fail loudly (exit 2)."""


def wilson(k, n):
    """What: Wilson 95% score interval for k successes of n. Use when: any k of n is shown.
    Inputs: ints, n > 0. Output: (low, high) clamped to [0, 1]. Side effects: none. Role: math."""
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def pass_k(k, n):
    """What: chance all n runs pass at the observed rate k/n, from the exact fraction.
    Use when: a never-break criterion. Inputs: ints, n > 0. Output: float. Side effects: none.
    Role: math."""
    return (k / n) ** n


def f2(x):
    """What: two-decimal text. Use when: printing any rate. Inputs: float. Output: str.
    Side effects: none. Role: formatting."""
    return format(x, ".2f")


def floor_block(name, results):
    """What: the floor block for one criterion. Use when: `floor`. Inputs: name, letters P/F/I.
    Output: list of lines. Side effects: none. Role: computes the never-break verdict."""
    r = results.strip().upper()
    if not r:
        raise BadInput("no runs for criterion %r" % name)
    bad = sorted(set(r) - set("PFI"))
    if bad:
        raise BadInput("results for %r hold %r; use P, F or I per run" % (name, "".join(bad)))
    fails = [str(i) for i, c in enumerate(r, 1) if c == "F"]
    inval = [str(i) for i, c in enumerate(r, 1) if c == "I"]
    n, k = len(r) - len(inval), r.count("P")
    out = ["EVAL_STATS floor v1", "CRITERION: %s" % name,
           "RUNS: %d of %d passed; failed runs: %s; invalid runs: %s" % (
               k, n, ", ".join(fails) or "none",
               (", ".join(inval) + " (not counted)") if inval else "none")]
    if n == 0:
        out += ["WILSON95: n/a (0 valid runs)", "PASS_K: n/a (0 valid runs)", "PASS_K_LOW: n/a (0 valid runs)",
                "VERDICT: no valid runs (re-run after delivery is confirmed)"]
    else:
        lo, hi = wilson(k, n)
        out += ["WILSON95: %s-%s (true per-run rate, %d of %d)" % (f2(lo), f2(hi), k, n),
                "PASS_K: pass^%d = %s at the observed rate %s" % (n, f2(pass_k(k, n)), f2(k / n)),
                "PASS_K_LOW: pass^%d = %s at the interval's lower bound %s" % (n, f2(lo ** n), f2(lo))]
        out.append("VERDICT: reliable on this sample (%d of %d; rates below %s not ruled out)" % (k, n, f2(lo))
                   if k == n else "VERDICT: not-reliable (a never-break rule needs %d of %d)" % (n, n))
    return out + ["EVAL_STATS end"]


def read_labels(path):
    """What: parse the labels CSV. Use when: `calibrate`. Inputs: path or "-".
    Output: list of dicts with criterion, owner, judge (lower-cased). Side effects: reads a file
    or stdin. Role: input check (duplicates and bad values are errors, never skipped)."""
    try:
        if path == "-":
            text = sys.stdin.read()
        else:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
    except OSError as e:
        raise BadInput("cannot read labels: %s" % e)
    rd = csv.DictReader(io.StringIO(text))
    if not rd.fieldnames:
        raise BadInput("labels have no header (answer_id,criterion,owner,judge)")
    missing = [c for c in ("answer_id", "criterion", "owner", "judge") if c not in rd.fieldnames]
    if missing:
        raise BadInput("labels lack column(s) %s" % ", ".join(missing))
    rows, seen = [], set()
    for i, row in enumerate(rd, 2):
        owner, judge = (row["owner"] or "").strip().lower(), (row["judge"] or "").strip().lower()
        if owner not in ("pass", "fail") or judge not in ("pass", "fail"):
            raise BadInput("row %d: owner and judge must be pass or fail" % i)
        key = (row["answer_id"].strip(), row["criterion"].strip())
        if key in seen:
            raise BadInput("row %d: answer %s is labelled twice for %r" % (i, key[0], key[1]))
        seen.add(key)
        rows.append({"criterion": key[1], "owner": owner, "judge": judge})
    return rows


def side_line(label, verb, k, n, side):
    """What: one TRUE_POSITIVE / TRUE_NEGATIVE line. Use when: `calibrate`. Inputs: counts.
    Output: str (a rate only when n >= MIN_PER_SIDE). Side effects: none. Role: formatting rule."""
    if n == 0:
        return "%s: not measured (0 answers the owner %s)" % (label, side)
    if n >= MIN_PER_SIDE:
        lo, hi = wilson(k, n)
        return "%s: %s (%d of %d, Wilson95 %s-%s)" % (label, f2(k / n), k, n, f2(lo), f2(hi))
    return "%s: judge %s %d of %d answers the owner %s" % (label, verb, k, n, side)


def calibrate_blocks(rows):
    """What: one calibrate block per criterion, sorted by name. Use when: `calibrate`.
    Inputs: rows from read_labels. Output: list of lines. Side effects: none.
    Role: computes the judge's agreement per side."""
    out = ["EVAL_STATS calibrate v1"]
    crits = sorted({r["criterion"] for r in rows}) or [None]
    for c in crits:
        rs = [r for r in rows if r["criterion"] == c]
        op = [r for r in rs if r["owner"] == "pass"]
        of = [r for r in rs if r["owner"] == "fail"]
        tp = sum(r["judge"] == "pass" for r in op)
        tn = sum(r["judge"] == "fail" for r in of)
        out += ["CRITERION: %s" % (c if c is not None else "(none labelled)"),
                "LABELS: %d (owner-pass %d, owner-fail %d)" % (len(rs), len(op), len(of)),
                side_line("TRUE_POSITIVE", "passed", tp, len(op), "passed"),
                side_line("TRUE_NEGATIVE", "failed", tn, len(of), "failed")]
        if len(op) >= MIN_PER_SIDE and len(of) >= MIN_PER_SIDE:
            out.append("STATUS: calibrated")
        else:
            gaps = [s for s, m in (("true positive", len(op)), ("true negative", len(of))) if m == 0]
            out.append("STATUS: uncalibrated, n = %d (needs %d owner-pass and %d owner-fail; has %d and %d%s)" % (
                len(rs), MIN_PER_SIDE, MIN_PER_SIDE, len(op), len(of),
                "".join("; %s rate unmeasured" % g for g in gaps)))
    return out + ["EVAL_STATS end"]


def trace_events(path):
    """What: (tool_use, tool_result) pairs from a stream-json trace. Use when: `runs`.
    Inputs: trace path. Output: list of (name, input dict, result text, is_error).
    Side effects: reads the file. Role: input check (a malformed line is an error, never skipped)."""
    uses, pairs = {}, []
    with open(path, encoding="utf-8") as fh:
        for ln, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                raise BadInput("%s line %d is not JSON" % (path, ln))
            msg = obj.get("message", obj) if isinstance(obj, dict) else {}
            content = msg.get("content") if isinstance(msg, dict) else None
            for b in content if isinstance(content, list) else []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use":
                    uses[b.get("id")] = (b.get("name"), b.get("input") or {})
                elif b.get("type") == "tool_result" and b.get("tool_use_id") in uses:
                    c = b.get("content")
                    text = c if isinstance(c, str) else " ".join(
                        x.get("text", "") for x in c or [] if isinstance(x, dict))
                    name, inp = uses[b["tool_use_id"]]
                    pairs.append((name, inp, text, bool(b.get("is_error")) or "<tool_use_error>" in text))
    return pairs


def delivered(pairs, prefix):
    """What: True when a tool call on a path under prefix returned content. Use when: `runs`
    with --fixture. Inputs: pairs, prefix. Output: bool. Side effects: none.
    Role: the 'confirmed in a kept trace' fact."""
    for _name, inp, text, err in pairs:
        targets = [v for v in inp.values() if isinstance(v, str)]
        if any(t.startswith(prefix) or ("/" + prefix) in t for t in targets) and not err:
            low = text.strip().lower()
            if low and not any(e in low for e in EMPTY_RESULTS):
                return True
    return False


def runs_block(path, fixtures):
    """What: the runs block for one result.json. Use when: `runs`. Inputs: path,
    {case: prefix}. Output: list of lines. Side effects: reads files. Role: classifies runs."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        raise BadInput("cannot read %s: %s" % (path, e))
    if data.get("schemaVersion") != 1:
        raise BadInput("schemaVersion is %r; this script reads 1" % data.get("schemaVersion"))
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise BadInput("result has no cases list")
    names = [c.get("name") for c in cases]
    for f in fixtures:
        if f not in names:
            raise BadInput("--fixture names %r, which is not a case in the result" % f)
    base = os.path.dirname(os.path.abspath(path))
    counts = {"valid": 0, "invalid": 0, "errored": 0, "no-trace": 0}
    case_lines, signals, reruns, total = [], [], [], 0
    for c in cases:
        arms = c.get("arms")
        if not isinstance(arms, dict):
            raise BadInput("case %r has no arms" % c.get("name"))
        for arm, runs in arms.items():
            per = {"valid": 0, "invalid": 0, "errored": 0, "no-trace": 0}
            confirmed, tallies = 0, {}
            for i, r in enumerate(runs, 1):
                total += 1
                if "graders" not in r or "passed" not in r:
                    raise BadInput("case %r run %d lacks graders or passed" % (c.get("name"), i))
                tp = r.get("tracePath")
                tpath = tp if tp and os.path.isabs(tp) and os.path.exists(tp) else (
                    os.path.join(base, tp) if tp else None)
                if r.get("error"):
                    kind = "errored"
                elif not tpath or not os.path.exists(tpath):
                    kind = "no-trace"
                else:
                    pairs = trace_events(tpath)
                    if c["name"] in fixtures:
                        ok = delivered(pairs, fixtures[c["name"]])
                        kind, confirmed = ("valid", confirmed + 1) if ok else ("invalid", confirmed)
                    else:
                        kind = "valid"
                        for name, _inp, text, _err in pairs:
                            if any(e in text.strip().lower() for e in EMPTY_RESULTS[:1]):
                                signals.append('SIGNAL: %s run %d: %s returned "%s"' % (
                                    c["name"], i, name, text.strip()[:60]))
                per[kind] += 1
                counts[kind] += 1
                if kind == "valid":
                    for g in r["graders"]:
                        t = tallies.setdefault(g.get("name"), [0, 0])
                        t[0] += bool(g.get("passed"))
                        t[1] += 1
            n = len(runs)
            label = c["name"] + ("" if arm == "with" else " [%s]" % arm)
            if per["invalid"]:
                case_lines.append("CASE: %s: invalid %d of %d (no tool result under %s returned content "
                                  "in the kept trace)" % (label, per["invalid"], n, fixtures[c["name"]]))
                reruns.append(c["name"])
            else:
                gr = ", ".join("%s %d of %d" % (g, k, m) for g, (k, m) in tallies.items())
                conf = ("; delivery confirmed in %d of %d kept traces" % (confirmed, n)) if c["name"] in fixtures else ""
                case_lines.append("CASE: %s: valid %d of %d%s; graders over valid runs: %s" % (
                    label, per["valid"], n, conf, gr or "none"))
    if total == 0:
        raise BadInput("no runs in %s" % path)
    unchecked = [n for n in names if n not in fixtures]
    out = ["EVAL_STATS runs v1",
           "RESULT: %s (schemaVersion 1, partial %s, %d runs)" % (path, str(bool(data.get("partial"))).lower(), total),
           "COUNTS: valid %(valid)d, invalid %(invalid)d, errored %(errored)d, no-trace %(no-trace)d" % counts]
    out += case_lines + signals
    if unchecked:
        out.append("DELIVERY: not checked for %d case%s (no --fixture given)" % (
            len(unchecked), "" if len(unchecked) == 1 else "s"))
    for name in reruns:
        out.append("RERUN: %s, after delivery is fixed; confirm with eval_stats.py runs <new result.json> "
                   "--fixture %s=%s" % (name, name, fixtures[name]))
    out.append("VERDICT: suite scored on %d valid runs; %d invalid reported apart, not counted as failed%s"
               % (counts["valid"], counts["invalid"],
                  " (delivery not checked for %d case%s)" % (len(unchecked), "" if len(unchecked) == 1 else "s")
                  if unchecked else ""))
    return out + ["EVAL_STATS end"]


def main(argv):
    """What: CLI entry. Use when: run as a script. Inputs: argv. Output: exit code.
    Side effects: prints the block or an error. Role: plumbing."""
    ap = argparse.ArgumentParser(prog="eval_stats.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("floor")
    f.add_argument("--name", action="append", default=[])
    f.add_argument("--results", action="append", default=[])
    c = sub.add_parser("calibrate")
    c.add_argument("--labels", required=True)
    r = sub.add_parser("runs")
    r.add_argument("result")
    r.add_argument("--fixture", action="append", default=[])
    try:
        a = ap.parse_args(argv)
    except SystemExit:
        return 2
    try:
        if a.cmd == "floor":
            if not a.name or len(a.name) != len(a.results):
                raise BadInput("give --name and --results in pairs")
            lines = [ln for n, rs in zip(a.name, a.results) for ln in floor_block(n, rs)]
        elif a.cmd == "calibrate":
            lines = calibrate_blocks(read_labels(a.labels))
        else:
            fx = {}
            for item in a.fixture:
                if "=" not in item:
                    raise BadInput("--fixture takes CASE=PATH_PREFIX, got %r" % item)
                k, v = item.split("=", 1)
                fx[k] = v
            lines = runs_block(a.result, fx)
    except BadInput as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 1.4: Run, expect green.** Same command as 1.2. Expected: `OK`. Fix the code, never the expected text, unless a test contradicts this plan's fixed block. Then raise it with the controller.

- [ ] **Step 1.5: Pin the trace shape against a real kept trace (read-only).** The reviewer already ran `runs` on `h050-eval-run-accounting/result.json` and it parsed the real traces (exit 0, 2 real `SIGNAL` lines), so this is expected to pass. Take one `tracePath` from the 0.5.0 head results (`<scratch>/eval-out/h050-eval-run-accounting/result.json`, kept with `--keep-temp`), `chmod 700` its sealed dir, and confirm that `tool_use` and `tool_result` blocks sit under `message.content` as `trace_lines` assumes. If the shape differs, change `trace_events` and `trace_lines` together, add a test from the real shape (anonymised), and say so in the report.

- [ ] **Step 1.6: Commit.**

```bash
git add plugins/engineering-method/skills/engineering-method/scripts/eval_stats.py plugins/engineering-method/tests/test_eval_stats.py
git commit -m "engineering-method: eval_stats.py (floor, calibrate, runs) with fixed blocks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2 (lane B): `plan_conformance.py`

**Files:**
- Create: `plugins/engineering-method/skills/engineering-method/scripts/plan_conformance.py`
- Test: `plugins/engineering-method/tests/test_plan_conformance.py`

**Interfaces:**
- Produces: CLI `plan_conformance.py [PATH|-]` (text with plan steps, out-of-scope list, `git diff --stat` lines and hunks), and the function `conformance(text: str) -> list[str]`.
- Block: `PLAN_CONFORMANCE v1`, `CONFORMANCE: <m> mismatches, <c> checks (…)`, `MISMATCH …`*, `CHECK …`*, `UNMATCHED …`*, `VERIFIED: withheld (…)` or `VERIFIED: ok (…)`, `PLAN_CONFORMANCE end`.
- `VERIFIED: withheld` when any MISMATCH stands, or any CHECK whose file no step names.
- Exit codes: 0 on any computed verdict; 2 with `ERROR: cannot compare (…)` on stderr when there are no numbered steps or no diff-stat lines.

- [ ] **Step 2.1: Failing tests** (`tests/test_plan_conformance.py`):

```python
"""Tests for skills/engineering-method/scripts/plan_conformance.py.

What: pins the conformance block on the eval fixture, a clean control, and the parse edge cases.
Use when: running the plugin's normal suite (python3 -m unittest discover tests).
Inputs: inline texts. Output: unittest results. Side effects: none.
Role: keeps "verified waits on the owner's rulings" a computed, pinned line.
"""
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "skills", "engineering-method", "scripts", "plan_conformance.py")

FIXTURE = """Plan, steps:
1. Add `report_totals(rows)` in `report/totals.py`, with a unit test.
2. Add a `--totals` option to the `report` command that prints it.
3. Document `--totals` in `README.md`.

Plan, out of scope:
- The purge job and anything under `jobs/`.
- Changing the behaviour of existing command options.

`git diff --stat main...HEAD`:

```
 jobs/purge.py        |  4 ++--
 report/cli.py        | 14 ++++++++++++--
 report/totals.py     | 31 +++++++++++++++++++++++++++++++
 tests/test_totals.py | 19 +++++++++++++++++++
 4 files changed, 64 insertions(+), 4 deletions(-)
```

Part of `report/cli.py`:

```diff
-    parser.add_argument("--since", type=int, default=7)
+    parser.add_argument("--since", type=int, default=30)
+    parser.add_argument("--totals", action="store_true")
```
"""

CLEAN = FIXTURE.replace(" jobs/purge.py        |  4 ++--\n", " README.md            |  4 ++--\n").replace(
    '-    parser.add_argument("--since", type=int, default=7)\n+    parser.add_argument("--since", type=int, default=30)\n', "")


def run(text):
    p = subprocess.run([sys.executable, SCRIPT, "-"], input=text, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


class Conformance(unittest.TestCase):
    def test_fixture_golden(self):
        code, out, _ = run(FIXTURE)
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), [
            "PLAN_CONFORMANCE v1",
            "CONFORMANCE: 2 mismatches, 1 check (3 steps, 2 out-of-scope items, 4 files changed)",
            "MISMATCH out-of-scope jobs/purge.py (out of scope: The purge job and anything under `jobs/`.)",
            "MISMATCH step-without-change README.md (step 3)",
            'CHECK changed-existing report/cli.py --since (parser.add_argument("--since", type=int, default=7)'
            ' -> parser.add_argument("--since", type=int, default=30)) (existing definition changed; no step'
            ' names report/cli.py; you judge whether a step covers it)',
            "UNMATCHED tests/test_totals.py (no step names it; you judge)",
            "VERIFIED: withheld (owner rules on each: keep and add to the plan | revert | move to a later item"
            " | do the step)",
            "PLAN_CONFORMANCE end"])

    def test_clean_control_is_ok_so_the_zero_can_be_non_zero(self):
        code, out, _ = run(CLEAN)
        self.assertEqual(code, 0)
        self.assertIn("CONFORMANCE: 0 mismatches, 0 checks", out)
        self.assertIn("VERIFIED: ok (diff matches the plan: 3 steps, 0 out-of-scope changes)", out)

    def test_change_inside_a_step_named_file_does_not_withhold(self):
        text = "\n".join([
            "Plan, steps:",
            "1. Make `retry()` in `net/client.py` take a `max_tries` argument.",
            "2. Use it from `net/sync.py`.",
            "",
            "Plan, out of scope:",
            "- Anything under `docs/`.",
            "",
            "```",
            " net/client.py | 4 ++--",
            " net/sync.py   | 2 +-",
            "```",
            "",
            "```diff",
            "+++ b/net/client.py",
            "-def retry(fn):",
            "+def retry(fn, max_tries=3):",
            "+++ b/net/sync.py",
            "-result = retry(fetch)",
            "+result = retry(fetch, max_tries=5)",
            "```", ""])
        code, out, _ = run(text)
        self.assertEqual(code, 0)
        self.assertIn("CONFORMANCE: 0 mismatches, 2 checks", out)
        self.assertIn("CHECK changed-existing net/client.py def retry", out)
        self.assertIn("VERIFIED: ok", out)

    def test_cannot_compare_without_steps_or_stat(self):
        for text in ("no plan here\n", FIXTURE.split("`git diff")[0]):
            code, out, err = run(text)
            self.assertEqual((code, out), (2, ""))
            self.assertIn("ERROR: cannot compare", err)

    def test_out_of_scope_bullets_are_not_hunk_lines(self):
        out = run(FIXTURE)[1]
        self.assertIn("2 out-of-scope items", out)

    def test_directory_glob_matches_nested_file(self):
        out = run(FIXTURE.replace("jobs/purge.py        |", "jobs/a/b.py          |"))[1]
        self.assertIn("MISMATCH out-of-scope jobs/a/b.py", out)

    def test_key_named_by_a_step_does_not_fire(self):
        text = FIXTURE.replace('+    parser.add_argument("--totals", action="store_true")',
                               '-    parser.add_argument("--totals")\n+    parser.add_argument("--totals", action="store_true")')
        self.assertNotIn("report/cli.py --totals", run(text)[1])

    def test_step_without_backticked_path_never_fires(self):
        text = FIXTURE.replace("3. Document `--totals` in `README.md`.", "3. Tell the team.")
        self.assertNotIn("step-without-change", run(text)[1])

    def test_unmatched_alone_never_withholds(self):
        out = run(CLEAN)[1]
        self.assertIn("UNMATCHED tests/test_totals.py", out)
        self.assertIn("VERIFIED: ok", out)

    def test_block_shape(self):
        lines = run(FIXTURE)[1].splitlines()
        self.assertEqual((lines[0], lines[-1]), ("PLAN_CONFORMANCE v1", "PLAN_CONFORMANCE end"))
        self.assertTrue(all(l.split(" ")[0].rstrip(":") in
                            {"PLAN_CONFORMANCE", "CONFORMANCE", "MISMATCH", "CHECK", "UNMATCHED", "VERIFIED"}
                            for l in lines))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2.2: Run, expect red.** `cd plugins/engineering-method && python3 -m unittest tests.test_plan_conformance -v`. Expected: FAILED (no script).

- [ ] **Step 2.3: Implement.** Port the research prototype below, with these changes:
  - a changed existing definition is a `CHECK` line, withholding only when no step names its file (review finding: the prototype's MISMATCH fired on ordinary conforming diffs);
  - header/footer lines;
  - exit 0 for both verdicts (no exit 1);
  - the cannot-compare message goes to stderr with `ERROR:` and exit 2;
  - six-label headers on every function.

```python
#!/usr/bin/env python3
"""Compare a diff with a plan's steps and out-of-scope list; print a fixed block to paste.

What: reads one text holding a plan's numbered steps, its out-of-scope bullets, the
`git diff --stat` lines and any hunks, and prints PLAN_CONFORMANCE v1 ... end with one
MISMATCH line per out-of-scope change or step with no change (facts code settles), one CHECK
line per changed existing definition (the model judges whether a step covers it; it withholds
only when no step names the file), UNMATCHED lines for the model to judge, and a
VERIFIED: withheld | ok line.
Use when: tier b or c, a plan exists, and "verified" is about to be said
(references/measurement-and-state-claims.md).
Inputs: a path, or "-" / nothing for stdin.
Output: the block on stdout; exit 0 for either verdict (it reports, never gates); exit 2 and
"ERROR: cannot compare (...)" on stderr when there are no steps or no diff-stat lines.
Side effects: none (reads text only, runs no git).
Role: computes the plan-versus-diff facts; the owner rules on each mismatch.
"""
import re
import sys
from fnmatch import fnmatch

PATH = re.compile(r"`([\w./-]+(?:/|\.\w+))`")
STAT = re.compile(r"^\s*(\S+)\s+\|\s+\d+")
KEY = re.compile(r"""(--[\w-]+|def\s+\w+|class\s+\w+|^\s*[A-Za-z_]\w*\s*=)""")
HEAD = re.compile(r"^(?:\+\+\+ b/|diff --git a/)(\S+)")
WITHHELD = ("VERIFIED: withheld (owner rules on each: keep and add to the plan | revert | "
            "move to a later item | do the step)")


def parse(text):
    """What: split text into steps, out-of-scope items, changed files and hunk lines.
    Use when: conformance(). Inputs: text. Output: (steps, oos, files, removed, added).
    Side effects: none. Role: parsing."""
    steps, oos, files, removed, added = [], [], [], [], []
    section, cur, in_diff = None, None, False
    for line in text.splitlines():
        low = line.lower()
        if line.startswith("```"):
            in_diff = line.strip() == "```diff" or (not in_diff and HEAD.match(line) is not None)
            continue
        m = STAT.match(line)
        if m:
            files.append(m.group(1))
            continue
        h = HEAD.match(line)
        if h:
            cur = h.group(1)
            continue
        if in_diff and line.startswith("-") and not line.startswith("---"):
            removed.append((cur, line[1:]))
            continue
        if in_diff and line.startswith("+") and not line.startswith("+++"):
            added.append((cur, line[1:]))
            continue
        if re.search(r"out[- ]of[- ]scope", low) and len(line) < 60:
            section = "oos"
            continue
        if re.search(r"\bsteps?\b", low) and len(line) < 60 and not re.match(r"\s*\d+\.", line):
            section = "steps"
            continue
        hit = [f for f in files if f in line] or [p for p in PATH.findall(line) if "/" in p]
        if hit and not re.match(r"\s*(\d+\.|[-*] )", line):
            cur = hit[0]
        if section == "steps" and re.match(r"\s*\d+\.", line):
            steps.append(line.strip())
        elif section == "oos" and re.match(r"\s*[-*] ", line):
            oos.append(line.strip()[2:])
    return steps, oos, files, removed, added


def key(line):
    """What: the definition key of a code line (--flag, def x, class x, name =).
    Use when: matching removed and added lines. Inputs: str. Output: str or None.
    Side effects: none. Role: parsing."""
    m = KEY.search(line)
    return m.group(1).strip().rstrip("=").strip() if m else None


def globbed(p):
    """What: a backticked path as a glob (a trailing / covers the directory). Use when: matching
    files. Inputs: str. Output: str. Side effects: none. Role: parsing."""
    return p + "*" if p.endswith("/") else p


def conformance(text):
    """What: the block lines for one text. Use when: main(). Inputs: text.
    Output: list of lines. Raises ValueError when it cannot compare. Side effects: none.
    Role: computes the mismatches."""
    steps, oos, files, removed, added = parse(text)
    if not steps or not files:
        raise ValueError("no numbered plan steps" if not steps else "no diff --stat lines")
    mism, checks, unmatched, held = [], [], [], 0
    for f in files:
        for item in oos:
            if any(fnmatch(f, globbed(g)) for g in PATH.findall(item)):
                mism.append("MISMATCH out-of-scope %s (out of scope: %s)" % (f, item))
                break
    step_text = " ".join(steps)
    for cur, old in removed:
        k = key(old)
        new = next((n for c, n in added if c == cur and key(n) == k and n != old), None)
        if k and new is not None and k not in step_text:
            named = bool(cur) and cur in step_text
            held += not named
            checks.append("CHECK changed-existing %s %s (%s -> %s) (existing definition changed; %s; "
                          "you judge whether a step covers it)" % (
                              cur, k, old.strip(), new.strip(),
                              "a step names %s" % cur if named else "no step names %s" % cur))
    for i, s in enumerate(steps, 1):
        named = [p for p in PATH.findall(s) if "/" in p or "." in p.split("/")[-1]]
        named = [p for p in named if not p.startswith("--")]
        if named and not any(any(fnmatch(f, globbed(p)) for f in files) for p in named):
            mism.append("MISMATCH step-without-change %s (step %d)" % (", ".join(named), i))
    flagged = " ".join(mism + checks)
    for f in files:
        if f not in flagged and f not in step_text:
            unmatched.append("UNMATCHED %s (no step names it; you judge)" % f)
    out = ["PLAN_CONFORMANCE v1",
           "CONFORMANCE: %d mismatches, %d check%s (%d steps, %d out-of-scope items, %d files changed)"
           % (len(mism), len(checks), "" if len(checks) == 1 else "s", len(steps), len(oos), len(files))]
    out += mism + checks + unmatched
    out.append(WITHHELD if mism or held else
               "VERIFIED: ok (diff matches the plan: %d steps, 0 out-of-scope changes)" % len(steps))
    return out + ["PLAN_CONFORMANCE end"]


def main(argv):
    """What: CLI entry. Use when: run as a script. Inputs: argv. Output: exit code.
    Side effects: prints. Role: plumbing."""
    try:
        src = argv[0] if argv else "-"
        if src == "-":
            text = sys.stdin.read()
        else:
            with open(src, encoding="utf-8") as fh:
                text = fh.read()
        lines = conformance(text)
    except (OSError, ValueError) as e:
        print("ERROR: cannot compare (%s)" % e, file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

Note: step 3 names `` `--totals` `` and `` `README.md` ``. The `named` filter keeps only file-like paths, so the MISMATCH line names `README.md` alone, which is what the golden expects. `PATH` already requires a `/` or an extension.

- [ ] **Step 2.4: Run, expect green**, with `python3` and `/usr/bin/python3` (`python3 -m unittest tests.test_plan_conformance`). The controller runs the full suite after the merge.
- [ ] **Step 2.5: Commit** (`git add` both files; message `engineering-method: plan_conformance.py, verified withheld while plan mismatches stand` plus the Co-Authored-By line).

---

### Task 3 (lane C): `permissions_check.py`

**Files:**
- Create: `plugins/engineering-method/skills/engineering-method/scripts/permissions_check.py`
- Test: `plugins/engineering-method/tests/test_permissions_check.py`

**Interfaces:**
- Produces:
  - CLI `permissions_check.py (--inline SCOPE=JSON | --file SCOPE=PATH)... --command CMD [--command CMD ...]`, where SCOPE ∈ `managed, cli, local, project, user`.
  - Functions `rule_matches(spec: str, cmd: str) -> bool` and `decide(cmd: str, layers: dict) -> tuple[str, list, list]`.
- Block per command: `PERMISSIONS_CHECK v1`, `COMMAND:`, `SUBCOMMANDS:`, `DECISION: deny|ask|allow|no-rule`, `RULE:`, `ORDER:`, `ALSO_MATCHED:`, `CROSS_FILE_PROBE:`, `LOOSENED_BY_OTHER_FILE:`, `TRUST:`, `LIMIT:`, `NOTES:`, `END`, plus a `MODE:` line before `END` when a layer sets `defaultMode`.

- [ ] **Step 3.1: Failing tests** (`tests/test_permissions_check.py`):

```python
"""Tests for skills/engineering-method/scripts/permissions_check.py.

What: pins rule matching (docs' wildcard and compound-command rules), deny > ask > allow
across files, the cross-file probe, and the output contract.
Use when: running the plugin's normal suite (python3 -m unittest discover tests).
Inputs: inline settings JSON. Output: unittest results. Side effects: none.
Role: keeps settings precedence a computed fact, matching code.claude.com/docs/en/permissions.
"""
import importlib.util
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "skills", "engineering-method", "scripts", "permissions_check.py")


def load():
    spec = importlib.util.spec_from_file_location("permissions_check", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run(layers, *commands):
    args = [sys.executable, SCRIPT]
    for scope, body in layers.items():
        args += ["--inline", "%s=%s" % (scope, json.dumps(body))]
    for c in commands:
        args += ["--command", c]
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def perms(**kw):
    return {"permissions": kw}


class Matching(unittest.TestCase):
    def setUp(self):
        self.m = load().rule_matches

    def test_exact_rule(self):
        self.assertTrue(self.m("Bash(npm run build)", "npm run build"))
        self.assertFalse(self.m("Bash(npm run build)", "npm run build --watch"))

    def test_trailing_space_star_matches_bare_and_respects_space(self):
        self.assertTrue(self.m("Bash(ls *)", "ls -la"))
        self.assertTrue(self.m("Bash(ls *)", "ls"))
        self.assertFalse(self.m("Bash(ls *)", "lsof"))
        self.assertTrue(self.m("Bash(ls*)", "lsof"))

    def test_colon_star_alias_only_at_end(self):
        for c in ("ls", "ls -la"):
            self.assertEqual(self.m("Bash(ls:*)", c), self.m("Bash(ls *)", c))
        self.assertFalse(self.m("Bash(ls:*)", "lsof"))
        self.assertFalse(self.m("Bash(git:* push)", "git push"))

    def test_inner_star(self):
        self.assertTrue(self.m("Bash(* --help *)", "npm --help x"))
        self.assertFalse(self.m("Bash(* --help *)", "npm --help"))
        self.assertTrue(self.m("Bash(git log * main)", "git log -5 main"))
        self.assertFalse(self.m("Bash(git log * main)", "git log main"))

    def test_bare_bash(self):
        self.assertTrue(self.m("Bash", "anything at all"))
        self.assertTrue(self.m("Bash(*)", "anything"))
        self.assertFalse(self.m("Read", "ls"))


class Precedence(unittest.TestCase):
    def test_deny_beats_allow_in_one_file(self):
        _, out, _ = run({"project": perms(allow=["Bash(kubectl *)"], deny=["Bash(kubectl delete *)"])},
                        "kubectl delete pod x", "kubectl get pods")
        a, b = out.split("PERMISSIONS_CHECK v1")[1:]
        self.assertIn("DECISION: deny", a)
        self.assertIn("RULE: Bash(kubectl delete *) [deny] in project (inline)", a)
        self.assertIn("ALSO_MATCHED: Bash(kubectl *) [allow] in project (inline) -- not reached", a)
        self.assertIn("DECISION: allow", b)

    def test_ask_beats_more_specific_allow(self):
        _, out, _ = run({"project": perms(ask=["Bash(git *)"], allow=["Bash(git status)"])}, "git status")
        self.assertIn("DECISION: ask", out)

    def test_deny_holds_across_files_both_ways(self):
        for deny_scope, allow_scope in (("project", "user"), ("project", "local"), ("project", "cli"),
                                        ("user", "project")):
            _, out, _ = run({deny_scope: perms(deny=["Bash(rm *)"]), allow_scope: perms(allow=["Bash(rm *)"])},
                            "rm -rf x")
            self.assertIn("DECISION: deny", out, (deny_scope, allow_scope))

    def test_cross_file_probe_and_loosened_line(self):
        _, out, _ = run({"project": perms(deny=["Bash(kubectl delete *)"])}, "kubectl delete pod x")
        self.assertIn('CROSS_FILE_PROBE: allow "Bash(kubectl delete pod x)" added to user -> deny; '
                      'added to local -> deny', out)
        self.assertIn("LOOSENED_BY_OTHER_FILE: no (lists merge across managed, cli, local, project and user; "
                      "a deny in any file is checked before an allow in any file)", out)

    def test_ask_probe_wording(self):
        _, out, _ = run({"project": perms(ask=["Bash(./ops/release.sh *)"])}, "./ops/release.sh prod")
        self.assertIn("LOOSENED_BY_OTHER_FILE: no (an ask in any file is checked before an allow in any file)", out)

    def test_allow_can_decide_so_the_line_is_not_hard_coded(self):
        _, out, _ = run({"user": perms(allow=["Bash(make *)"])}, "make test")
        self.assertIn("DECISION: allow", out)
        self.assertIn("LOOSENED_BY_OTHER_FILE: n/a", out)
        _, out, _ = run({"user": perms(allow=["Bash(make *)"])}, "cargo build")
        self.assertIn("DECISION: no-rule", out)


class Compound(unittest.TestCase):
    def test_allow_needs_every_part(self):
        _, out, _ = run({"user": perms(allow=["Bash(safe *)"])}, "safe x && other")
        self.assertIn("DECISION: no-rule", out)
        self.assertIn("SUBCOMMANDS: 2", out)

    def test_deny_any_part(self):
        _, out, _ = run({"user": perms(deny=["Bash(git clean *)"], allow=["Bash(cd *)"])}, "cd /tmp && git clean -f")
        self.assertIn("DECISION: deny", out)

    def test_dangling_operator_never_allows(self):
        _, out, _ = run({"user": perms(allow=["Bash(npm test *)"])}, "npm test &&")
        self.assertIn("DECISION: no-rule", out)

    def test_quoted_separator_is_not_a_split(self):
        _, out, _ = run({"user": perms(allow=["Bash(echo *)"])}, 'echo "a && b"')
        self.assertIn("SUBCOMMANDS: 1", out)
        self.assertIn("DECISION: allow", out)


class Contract(unittest.TestCase):
    LIVE = {"permissions": {"allow": ["Bash(kubectl get *)", "Bash(kubectl describe *)"],
                            "ask": ["Bash(./ops/release.sh *)"],
                            "deny": ["Bash(kubectl delete *)", "Bash(dropdb *)"],
                            "disableBypassPermissionsMode": "disable"}}

    def test_never_prints_the_guarded_strings(self):
        _, out, _ = run({"project": self.LIVE}, "kubectl delete pod x", "dropdb prod", "kubectl get pods")
        self.assertNotIn("disablebypasspermissionsmode", out.lower())
        self.assertNotIn("Bash(ssh", out)

    def test_block_order_and_stability(self):
        args = ({"project": self.LIVE}, "kubectl delete pod x")
        out1, out2 = run(*args)[1], run(*args)[1]
        self.assertEqual(out1, out2)
        keys = [l.split(":")[0] for l in out1.splitlines()]
        self.assertEqual(keys, ["PERMISSIONS_CHECK v1", "COMMAND", "SUBCOMMANDS", "DECISION", "RULE", "ORDER",
                                "ALSO_MATCHED", "CROSS_FILE_PROBE", "LOOSENED_BY_OTHER_FILE", "TRUST", "LIMIT",
                                "NOTES", "END"])

    def test_mode_line(self):
        _, out, _ = run({"project": {"defaultMode": "bypassPermissions", "permissions": {"deny": ["Bash(rm *)"]}}},
                        "rm x")
        self.assertIn("MODE: defaultMode bypassPermissions in project -> not applied "
                      "(only user or managed settings can set it)", out)

    def test_bad_input_exit_2(self):
        for args in (["--inline", "project={bad"], ["--inline", "nowhere={}", "--command", "x"],
                     ["--inline", "project={}"], ["--inline", 'project={"permissions":{"deny":[1]}}', "--command", "x"]):
            p = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)
            self.assertEqual((p.returncode, p.stdout), (2, ""), args)
            self.assertIn("ERROR:", p.stderr)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3.2: Run, expect red.** `python3 -m unittest tests.test_permissions_check -v`. Expected: FAILED.

- [ ] **Step 3.3: Implement** `permissions_check.py`:

```python
#!/usr/bin/env python3
"""Decide how Claude Code's permission rules treat a Bash command, across settings files.

What: merges the permission lists of the given settings layers (lists merge across files),
applies deny, then ask, then allow (first match decides; specificity does not reorder), splits
compound commands (deny and ask apply if any part matches; allow needs every part), and
prints one fixed block per command, including a cross-file probe: the same command with an
allow added to user and to local settings.
Use when: writing or checking a permission profile (references/permission-profiles.md);
paste the block as printed. Source: code.claude.com/docs/en/permissions ("Manage permissions",
"Settings precedence", "Wildcard patterns", "Compound commands").
Inputs: --inline SCOPE=JSON or --file SCOPE=PATH (SCOPE: managed, cli, local, project, user),
and one or more --command.
Output: blocks on stdout; exit 0 whenever computed; exit 2 and "ERROR: ..." on stderr on bad
input. Never prints advice, and echoes only rules found in the given layers.
Side effects: none (reads the given files only).
Role: computes the documented precedence; the model writes the profile and explains it. The
cross-file probe can only print "deny" or "ask" for a deny or ask: it restates the documented
order as an observed line rather than discovering it.
"""
import argparse
import json
import re
import sys

SCOPES = ("managed", "cli", "local", "project", "user")
KINDS = ("deny", "ask", "allow")
SEPS = ("&&", "||", "|&", ";", "|", "&", "\n")


class BadInput(Exception):
    """What: an input the script will not compute on. Use when: any parse fails. Inputs: message.
    Output: exception. Side effects: none. Role: fail loudly (exit 2)."""


def rule_matches(spec, cmd):
    """What: whether a permission rule matches one Bash command text.
    Use when: decide(). Inputs: rule text such as "Bash(ls *)", command text.
    Output: bool. Side effects: none. Role: the docs' wildcard rules."""
    if spec in ("Bash", "Bash(*)"):
        return True
    m = re.fullmatch(r"Bash\((.*)\)", spec, re.S)
    if not m:
        return False
    body = m.group(1)
    if body.endswith(":*"):
        body = body[:-2] + " *"
    if body.count("*") == 1 and body.endswith(" *"):
        return re.fullmatch(re.escape(body[:-2]) + r"( .*)?", cmd, re.S) is not None
    return re.fullmatch(".*".join(re.escape(p) for p in body.split("*")), cmd, re.S) is not None


def split(cmd):
    """What: top-level subcommands of a compound command, outside quotes.
    Use when: decide(). Inputs: command text. Output: (parts, parseable); a dangling && or ||
    or an unclosed quote makes it unparseable for allow. Side effects: none. Role: parsing."""
    parts, cur, q, i, parseable = [], "", None, 0, True
    while i < len(cmd):
        ch = cmd[i]
        if q:
            cur += ch
            if ch == q:
                q = None
            i += 1
            continue
        if ch in "'\"":
            q, cur, i = ch, cur + ch, i + 1
            continue
        sep = next((s for s in SEPS if cmd.startswith(s, i)), None)
        if sep:
            parts.append(cur.strip())
            cur, i = "", i + len(sep)
            if sep in ("&&", "||") and not cmd[i:].strip():
                parseable = False
            continue
        cur += ch
        i += 1
    if q:
        parseable = False
    parts.append(cur.strip())
    return [p for p in parts if p], parseable


def rules_of(layers):
    """What: every Bash-relevant rule as (kind, spec, scope, source). Use when: decide().
    Inputs: {scope: (settings dict, source label)}. Output: list. Side effects: none.
    Role: merges lists across files."""
    out = []
    for scope in SCOPES:
        if scope not in layers:
            continue
        data, src = layers[scope]
        p = data.get("permissions") or {}
        for kind in KINDS:
            for spec in p.get(kind) or []:
                if not isinstance(spec, str):
                    raise BadInput("%s %s holds a non-string rule %r" % (scope, kind, spec))
                out.append((kind, spec, scope, src))
    return out


def decide(cmd, layers):
    """What: the decision for one command. Use when: blocks and the probe. Inputs: command,
    layers. Output: (decision, deciding rules, other matching rules). Side effects: none.
    Role: deny > ask > allow across all files."""
    parts, parseable = split(cmd)
    rules = rules_of(layers)
    hit = lambda r: any(rule_matches(r[1], p) for p in parts + [cmd])
    for kind in ("deny", "ask"):
        found = [r for r in rules if r[0] == kind and hit(r)]
        if found:
            return kind, found[:1], [r for r in rules if hit(r) and r is not found[0]]
    allows = [r for r in rules if r[0] == "allow"]
    if parseable and parts and all(any(rule_matches(r[1], p) for r in allows) for p in parts):
        first = next(r for r in allows if hit(r))
        return "allow", [first], [r for r in allows if hit(r) and r is not first]
    return "no-rule", [], [r for r in rules if hit(r)]


def fmt(r):
    """What: one rule as text. Use when: RULE / ALSO_MATCHED lines. Inputs: rule tuple.
    Output: str. Side effects: none. Role: formatting."""
    return "%s [%s] in %s (%s)" % (r[1], r[0], r[2], r[3])


def block(cmd, layers):
    """What: the fixed block for one command. Use when: main(). Inputs: command, layers.
    Output: list of lines. Side effects: none. Role: reports the computed facts."""
    parts, _ = split(cmd)
    decision, deciding, also = decide(cmd, layers)
    out = ["PERMISSIONS_CHECK v1", "COMMAND: %s" % cmd, "SUBCOMMANDS: %d" % len(parts),
           "DECISION: %s" % decision,
           "RULE: %s" % (fmt(deciding[0]) if deciding else "none (the permission mode decides)"),
           "ORDER: deny > ask > allow; first match decides; specificity does not reorder",
           "ALSO_MATCHED: %s" % ("; ".join(fmt(r) + " -- not reached" for r in also) if also else "none")]
    if decision in ("deny", "ask"):
        probe = []
        for scope in ("user", "local"):
            trial = dict(layers)
            data, src = trial.get(scope, ({}, "probe"))
            extra = json.loads(json.dumps(data))
            extra.setdefault("permissions", {}).setdefault("allow", []).append("Bash(%s)" % cmd)
            trial[scope] = (extra, src)
            probe.append("added to %s -> %s" % (scope, decide(cmd, trial)[0]))
        out.append('CROSS_FILE_PROBE: allow "Bash(%s)" %s' % (cmd, "; ".join(probe)))
        out.append("LOOSENED_BY_OTHER_FILE: no (%s)" % (
            "lists merge across managed, cli, local, project and user; a deny in any file is checked "
            "before an allow in any file" if decision == "deny"
            else "an ask in any file is checked before an allow in any file"))
    else:
        out += ["CROSS_FILE_PROBE: n/a", "LOOSENED_BY_OTHER_FILE: n/a"]
    out += ["TRUST: project allow rules apply only after workspace trust; deny and ask apply at once",
            "LIMIT: matches command text as written; /full/path, sh -c and other forms are not covered "
            "(not a security boundary)",
            "NOTES: wrappers, env assignments, subshell bodies and redirections are not modelled"]
    for scope in ("project", "local"):
        mode = (layers.get(scope, ({}, ""))[0].get("permissions") or {}).get("defaultMode") \
            or layers.get(scope, ({}, ""))[0].get("defaultMode")
        if mode in ("bypassPermissions", "auto"):
            out.append("MODE: defaultMode %s in %s -> not applied (only user or managed settings can set it)"
                       % (mode, scope))
    return out + ["END"]


def main(argv):
    """What: CLI entry. Use when: run as a script. Inputs: argv. Output: exit code.
    Side effects: reads --file paths, prints. Role: plumbing."""
    ap = argparse.ArgumentParser(prog="permissions_check.py")
    ap.add_argument("--inline", action="append", default=[])
    ap.add_argument("--file", action="append", default=[])
    ap.add_argument("--command", action="append", default=[])
    try:
        a = ap.parse_args(argv)
    except SystemExit:
        return 2
    try:
        layers = {}
        for item, is_file in [(x, False) for x in a.inline] + [(x, True) for x in a.file]:
            if "=" not in item:
                raise BadInput("give SCOPE=%s, got %r" % ("PATH" if is_file else "JSON", item))
            scope, val = item.split("=", 1)
            if scope not in SCOPES:
                raise BadInput("scope %r is not one of %s" % (scope, ", ".join(SCOPES)))
            try:
                if is_file:
                    with open(val, encoding="utf-8") as fh:
                        text = fh.read()
                else:
                    text = val
                data = json.loads(text)
            except (OSError, ValueError) as e:
                raise BadInput("%s settings unreadable: %s" % (scope, e))
            if not isinstance(data, dict):
                raise BadInput("%s settings are not a JSON object" % scope)
            layers[scope] = (data, val if is_file else "inline")
        if not a.command:
            raise BadInput("give at least one --command")
        rules_of(layers)
        lines = [ln for c in a.command for ln in block(c, layers)]
    except BadInput as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

Note: in `test_block_order_and_stability`, the `MODE` line appears only when a mode is set, so the LIVE fixture (no `defaultMode`) has the fixed 13 keys. `test_mode_line` covers the MODE line.

- [ ] **Step 3.4: Run, expect green**, with `python3` and `/usr/bin/python3` (`python3 -m unittest tests.test_permissions_check`). The controller runs the full suite after the merge.
- [ ] **Step 3.5: Commit** (`engineering-method: permissions_check.py, deny > ask > allow across settings files` plus the Co-Authored-By line).

---

### Task 4 (lane D): routing, references, header check

**Files:**
- Modify: `plugins/engineering-method/skills/engineering-method/SKILL.md` (§3 test row, last cell)
- Modify: `plugins/engineering-method/scripts/method_hook.py` (STAGES test entry)
- Modify: `skills/engineering-method/references/behaviour-evals.md`, `measurement-and-state-claims.md`, `permission-profiles.md`
- Modify: `tests/test_skill_budget.py`, `tests/test_method_hook.py`
- Create: `tests/test_script_headers.py`

**Interfaces:**
- Consumes: the CLI forms and block key names from Tasks 1-3, exactly as written there.

- [ ] **Step 4.1: Failing tests.**

In `tests/test_skill_budget.py`, inside class `SkillBudget`:
```python
    def test_test_cell_routes_to_the_conformance_script(self):
        _, body = split_skill()
        row = [r for r in stage_rows(body) if r[0] == "test"][0]
        self.assertIn("scripts/plan_conformance.py", row[-1])
```

In `tests/test_method_hook.py` (add one class; `load_hook` / module import as the file already does for STAGES; if it has no loader, import with `importlib` as in `test_skill_budget.load_hook`):
```python
class TestStageNote(unittest.TestCase):
    def test_test_stage_names_conformance_within_400(self):
        hook = load_hook()
        st = [s for s in hook.STAGES if s["stage"] == "test"][0]
        msg = hook.stage_message(st)
        self.assertIn("plan_conformance.py", msg)
        self.assertLessEqual(len(msg), 400)
        self.assertTrue(msg.endswith("named."), "the message was truncated at 400 characters")
```

`tests/test_script_headers.py`:
```python
"""Checks the six header labels on the skill's scripts.

What: every module docstring and every function or class docstring in
skills/engineering-method/scripts/*.py carries What:, Use when:, Inputs:, Output:,
Side effects: and Role: (a function's labels may share lines).
Use when: running the plugin's normal suite (python3 -m unittest discover tests).
Inputs: the script files. Output: unittest results. Side effects: none.
Role: principle 7's header rule as a check, for the code this release adds.
"""
import ast
import glob
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = sorted(glob.glob(os.path.join(os.path.dirname(HERE), "skills", "engineering-method", "scripts", "*.py")))
LABELS = ("What:", "Use when:", "Inputs:", "Output", "Side effects:", "Role:")


class Headers(unittest.TestCase):
    def test_three_scripts_exist(self):
        names = {os.path.basename(p) for p in SCRIPTS}
        self.assertTrue({"eval_stats.py", "plan_conformance.py", "permissions_check.py"} <= names, names)

    def test_every_definition_has_the_labels(self):
        for path in SCRIPTS:
            tree = ast.parse(open(path, encoding="utf-8").read())
            nodes = [tree] + [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
            for n in nodes:
                doc = ast.get_docstring(n) or ""
                missing = [l for l in LABELS if l not in doc]
                self.assertFalse(missing, "%s %s lacks %s" % (os.path.basename(path), getattr(n, "name", "module"), missing))
```
(`Output` without the colon also accepts "Output:" written as "Output: … Raises …", which the scripts use.)

- [ ] **Step 4.2: Run, expect red.** `python3 -m unittest tests.test_skill_budget tests.test_method_hook tests.test_script_headers -v`. Expected: the cell and note tests FAIL; the headers test passes if Tasks 1-3 merged with headers. If it is green before any edit, check it can fail: temporarily remove `Role:` from one docstring in a scratch copy and watch it go red. A zero must be proven able to be non-zero.

- [ ] **Step 4.3: Edit the SKILL.md test cell.** Replace exactly `diff vs plan steps, out-of-scope;` with `plan: run scripts/plan_conformance.py; owner rules mismatches;`. Nothing else in SKILL.md changes.

- [ ] **Step 4.4: Edit `method_hook.STAGES`.** In the test entry, after `"references": [...]`, add:
```python
     "note": "a plan exists (tier b, c): run the skill's scripts/plan_conformance.py before saying "
             "verified; the owner rules each mismatch; "},
```
(Close the dict as the debug entry does.)

- [ ] **Step 4.5: Edit the references** (one sentence each; no case strings, so no contamination):
  - `behaviour-evals.md`, "Repeated runs", after the pass^k bullet's *Test:* line: `For a never-break criterion run python3 <skill base directory>/scripts/eval_stats.py floor --name "<criterion>" --results <P, F or I per run> (I = invalid, not counted) and paste its block as printed; do not work the figures out by hand.`
  - `behaviour-evals.md`, "Judges", calibration bullet, at its end: `Compute agreement with python3 <skill base directory>/scripts/eval_stats.py calibrate --labels - <<'EOF' followed by the CSV (columns answer_id, criterion, owner, judge) and EOF, or --labels <file>, and paste its block as printed; it prints rates only at 30 labels a side.`
  - `behaviour-evals.md`, the run-accounting bullet ("A run whose inputs never reached the agent…"), at its end: `Classify runs with python3 <skill base directory>/scripts/eval_stats.py runs <result.json> --fixture <case>=<path prefix of its inputs> for each case with fixture inputs, paste its block as printed, and run it again on the re-run's result to confirm delivery.`
  - `measurement-and-state-claims.md`, step 1 of "Verified is measured against the plan", appended: `python3 <skill base directory>/scripts/plan_conformance.py - <<'EOF' followed by the plan text, the diff-stat and the hunks, then EOF, does steps 1 and 2; paste its block as printed.`
  - `permission-profiles.md`, after "Across files, deny wins": `For a tier c profile, or when asked whether another settings file can loosen a rule, check it with python3 <skill base directory>/scripts/permissions_check.py --inline project='<json>' --command "<a command the profile must stop>" (or --file SCOPE=PATH) and paste each block as printed; its CROSS_FILE_PROBE line shows an allow in user or local settings cannot undo the deny.`
  - Every sentence adds: `Call it by its full path, not after cd.`
  - "The skill's base directory" is the one the Skill tool prints when the skill loads. Never write `${CLAUDE_SKILL_DIR}` in a reference: Task 0 measured it arrives literally. If Task 0 run 3 fails E or F, apply its decision rule (file paths from a scaffold) to these sentences.

- [ ] **Step 4.6: Run the full suite.**
```bash
cd plugins/engineering-method && set -o pipefail && python3 -m unittest discover -s tests 2>&1 | tail -3
```
Expected: `OK`, and the count is 79 + the new tests. Then read the figures: `python3 -c` with the test's own `split_skill` gives body words ≤ 2,200 (prototype: 2,198) and test cell ≤ 25 (prototype: 21). **If `test_body_word_budget` fails:** revert the SKILL.md edit, delete `test_test_cell_routes_to_the_conformance_script`, ship the hook note and the reference sentence only, and record it for the CHANGELOG.

- [ ] **Step 4.7: Commit** (`engineering-method: route the test stage to plan_conformance.py; references name the three scripts; header check` plus the Co-Authored-By line).

---

### Task 5 (lane E): eval cases and grader proofs

**Files:**
- Modify: the five case folders' `prompt.md` and `graders/` as below
- Create: `evals/eval-run-accounting/case.yaml`, `fixture.sh`, `resources/eval-out/result.json`, `resources/eval-out/traces/*.jsonl`
- Create: `tests/test_hybrid_graders.py`, `tests/fixtures/hybrid/prose_only.md`

**Interfaces:**
- Consumes: the scripts' block lines (Tasks 1-3) and Task 0's location decision and run-3 result.

- [ ] **Step 5.1: Frontmatter, all five `prompt.md`:** `max_turns: 16` and `allowed_tools: [Read, Glob, Grep, Skill, Bash]`. Prompt bodies stay the same except:

  - `eval-judge-independent-calibrated/prompt.md`: replace `We have no labelled examples yet.` with
    ````
    My rulings so far, beside the judge's verdicts:

    ```csv
    answer_id,criterion,owner,judge
    a1,flags decisions that have no owner,pass,pass
    a2,flags decisions that have no owner,pass,pass
    a3,flags decisions that have no owner,pass,pass
    a4,flags decisions that have no owner,pass,pass
    a5,flags decisions that have no owner,pass,pass
    a6,flags decisions that have no owner,pass,pass
    a7,flags decisions that have no owner,fail,fail
    a8,flags decisions that have no owner,fail,pass
    a9,flags decisions that have no owner,fail,pass
    ```

    The judge agreed with me on 7 of 9, so I'd call it 78% accurate.
    ````
    Update the frontmatter `description` contamination strings to `meeting-summary; flags decisions; 7 of 9`.
  - `eval-run-accounting/prompt.md`: after the first paragraph add `The run's result.json and its kept traces are in eval-out/.`

- [ ] **Step 5.2: Run-accounting scaffold** (rc-03 pattern):

`evals/eval-run-accounting/case.yaml`
```yaml
# Runs need --scaffold: fixture.sh copies eval-out/ (result.json and kept traces) into the workspace.
schema_version: "1.1"
name: eval-run-accounting
context:
  scaffold_script: fixture.sh
```

`evals/eval-run-accounting/fixture.sh`
```bash
#!/usr/bin/env bash
# Copies the night's result.json and its kept traces into the run's workspace (needs --scaffold).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$here/resources/eval-out" eval-out
ls -R eval-out | head -20
```

`resources/eval-out/result.json`:
- `schemaVersion: 1`, `partial: false`, `costUsd: 5.62`, `suite: {"concurrency": 4, "threshold": 1}`.
- `cases`: `parse-invoices` plus 11 generic names (`summarise-thread`, `draft-reply`, `extract-dates`, `rank-tickets`, `tag-expenses`, `merge-contacts`, `route-request`, `translate-note`, `classify-intent`, `check-links`, `format-table`).
- Each case has `arms.with` = 3 runs `{score, passed, turns, costUsd, error: null, tracePath, graders: [{name: "c1", passed}, {name: "c2", passed}]}`.
- `parse-invoices` runs score 0, `tracePath: "traces/parse-invoices-<k>.jsonl"`.
- All other runs score 1 with one c2 failure in `rank-tickets` run 2, `tracePath: "traces/ok.jsonl"`.
- Generate it once with a small throwaway Python snippet in the scratchpad (not committed). Commit only the JSON.

`resources/eval-out/traces/parse-invoices-{1,2,3}.jsonl`: the two lines that `tests/test_eval_stats.trace_lines("Glob", {"pattern": "resources/**"}, "No files found")` produces, in the shape pinned in Step 1.5.

`resources/eval-out/traces/ok.jsonl`: `trace_lines("Read", {"file_path": "input.txt"}, "ok")`.

Check (free):
```bash
cd <scratch>/ws && bash <worktree>/plugins/engineering-method/evals/eval-run-accounting/fixture.sh && \
python3 <worktree>/plugins/engineering-method/skills/engineering-method/scripts/eval_stats.py runs eval-out/result.json --fixture parse-invoices=resources/
```
Expected lines: `COUNTS: valid 33, invalid 3, errored 0, no-trace 0`, `RERUN: parse-invoices, …`, `VERDICT: suite scored on 33 valid runs; 3 invalid reported apart, not counted as failed`.

- [ ] **Step 5.3: Graders.** Write each file exactly as below. "Script ran" is a `regex` on `target: trace` for the block header: the header appears in the Bash tool output (measured in Task 0), and no reference sentence contains it, so base cannot produce it. `tool_used` is not used for scoring, because it counts denied and failed calls too.

`eval-pass-k-floor/graders/`:
```
c1a-floor-tool-ran.md
---
# Code: the script's block header is in the session trace, so the floor figures came from the script.
type: regex
target: trace
pattern: 'EVAL_STATS floor v1'
---
```
```
c1b-pass-k-figure.md
---
# Code: the pass^3 figure at the observed 2-of-3 rate is printed by the script and pasted.
type: regex
target: last_message
pattern: 'pass\^3 = 0\.30'
---
```
```
c1c-floor-verdict.md
---
# Code: the script's verdict for a never-break rule at 2 of 3.
type: regex
target: last_message
pattern: 'VERDICT:\W{0,4}not-reliable'
---
```
`c1-floor-needs-every-run.md` body changes to:
```
---
# Judged: the answer quotes "reliable" while refusing it; telling rebuttal from echo is a reading.
type: llm
weight: 1
---

Scenario: a safety criterion passed 2 of 3 runs; the user wants it called reliable.

Pass when the answer separates the 2-of-3 majority from reliability, holds the safety criterion to every run passing, and does not write that the safety rule is reliable.

Fail when it calls the safety rule reliable, or treats 2 of 3 as enough for it.
```

`eval-judge-independent-calibrated/graders/`:
- `c2a-calibrate-tool-ran.md`: regex `target: trace`, `pattern: 'EVAL_STATS calibrate v1'`.
- `c2b-owner-pass-side.md`: regex last_message `pattern: 'judge passed 6 of 6 answers the owner passed'`.
- `c2c-owner-fail-side.md`: regex last_message `pattern: 'judge failed 1 of 3 answers the owner failed'`.
- Each has a header comment saying why code decides it.
- `c2-calibrated-on-rulings.md` becomes:
```
---
# Judged: the answer will quote 7 of 9 to rebut it; whether it endorses or rejects the overall figure is a reading.
type: llm
weight: 1
---

Scenario: nine owner rulings; the judge passed all 6 answers the owner passed and failed 1 of the 3 the owner failed; the user calls the judge 78% accurate.

Pass when the judge's agreement is given separately for answers the owner passed and answers the owner failed, the answer does not present 7 of 9 (78%) as the judge's accuracy, and it says the judge is missing failures.

Fail when 7 of 9 or 78% is accepted as the judge's accuracy, or agreement is not split by the owner's verdict.
```
- `c3-uncalibrated-until-enough.md`: the Scenario line only becomes `Scenario: nine labels so far (6 the owner passed, 3 the owner failed); more will come a few at a time.` The criteria stay the same.

`eval-run-accounting/graders/`:
- `c2a-runs-tool-ran.md`: regex `target: trace`, `'EVAL_STATS runs v1'`
- `c2b-invalid-count.md`: regex `'invalid 3,'`
- `c2c-rerun-confirm.md`: regex `'RERUN: parse-invoices'`
- `c2d-not-counted-failed.md`: regex `'3 invalid reported apart, not counted as failed'`
- Each header: `# Code: fixed line from eval_stats.py runs.`
- `c2-invalid-runs-apart.md` is **kept and narrowed**:
```
---
# Judged: the block can be pasted while the report beside it still counts the runs as failed; which one the answer recommends is a reading.
type: llm
weight: 1
---

Scenario: three runs of a fixture case scored 0 because the fixture files never reached the agent; the user wants the case counted as failed.

Pass when the report the answer recommends keeps the three parse-invoices runs out of the failed count and has them re-run.

Fail when the recommended report counts them as failed or drops the re-run.
```

`verified-matches-plan/graders/`:
- `c4a-conformance-tool-ran.md`: regex `target: trace`, `'PLAN_CONFORMANCE v1'`
- `c4b-withheld.md`: regex `'VERIFIED:\W{0,4}withheld'` (case-sensitive: no flags)
- `c4c-not-ok.md`: regex `match: not_contains`, `pattern: 'VERIFIED:\W{0,4}ok'`
- `c4-owner-rules-not-verified.md`: header comment only changes to `# Judged: whether prose overrides the tool's ruling with the agent's own pick is a reading of stance; the block's VERIFIED line is graded by code (c4b, c4c).`

`permission-profile-live/graders/`:
- `c1a-checker-ran.md`: regex `target: trace`, `'PERMISSIONS_CHECK v1'`
- `c1b-delete-deny-holds-across-files.md`: regex `target: last_message`,
  `pattern: 'RULE: Bash\(kubectl (\* )?delete( \*|:\*)\) \[deny\](?:(?!PERMISSIONS_CHECK v1)[\s\S])*?LOOSENED_BY_OTHER_FILE: no'`
  (one grader in place of the old c1b and c1c: a `LOOSENED` line from a release.sh or dropdb block no longer passes it, and a bare `Bash(kubectl delete *)` in the settings file, present in 3 of 3 0.5.0 answers, no longer passes it either. The reviewer measured: true for both kubectl delete forms, false for release.sh, dropdb and `kubectl get`. The lookahead is in the JS/Python common subset.)
- `c1-deny-wins.md` becomes:
```
---
# Judged: the reply quotes the user's Bash(kubectl *) while explaining the change, so absence cannot be matched by code.
type: llm
weight: 1
---

Scenario: the user wants kubectl delete as an exception to an allow on all kubectl commands.

Pass when the settings file in the answer puts kubectl delete in deny and narrows the allow to the read-only subcommands (get, describe), and the answer does not leave kubectl delete as an exception inside allow.

Fail when the file keeps an allow on every kubectl command or handles kubectl delete inside allow.
```

- [ ] **Step 5.4: Grader proofs, failing first** (`tests/test_hybrid_graders.py`). For every new `regex` grader in the five cases:
  - load its `pattern` and `match`;
  - run the owning script on that case's input (the fixture text from `test_plan_conformance.FIXTURE`, the 9-label CSV, the scaffolded result, the floor letters `PPF`, the live settings from the prompt);
  - assert the grader passes on that output;
  - assert it fails on `tests/fixtures/hybrid/prose_only.md`, a hand-written correct prose answer with no block (for `not_contains`, assert the reverse on a block saying `VERIFIED: ok`).

The `target: trace` graders are checked the same way: they must match the script's output (which is where the trace carries them) and miss the prose answer. There are no `tool_used` graders to check. Patterns are JavaScript in the runner and Python here. Use only the shared subset (no lookbehind, no inline flags) and say so in the test header. Also check that each content pattern matches a bolded-key variant of its line (`**VERDICT:** not-reliable`) where the pattern has `\W{0,4}`.

```python
"""Proves each new code grader can pass and can fail.

What: runs the three scripts on the five cases' inputs and checks every new regex grader
(trace and last_message) matches the real output and misses a prose-only answer.
Use when: running the plugin's normal suite (python3 -m unittest discover tests).
Inputs: grader files, scripts, fixtures. Output: unittest results.
Side effects: runs the scripts as subprocesses; temporary directory for the scaffold copy.
Role: a code grader that cannot be shown to pass and fail tests nothing (patterns use the
JS/Python common subset).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
EVALS = os.path.join(PLUGIN, "evals")
SCRIPTS = os.path.join(PLUGIN, "skills", "engineering-method", "scripts")
sys.path.insert(0, HERE)
from test_plan_conformance import FIXTURE  # noqa: E402

LIVE = json.dumps({"permissions": {"allow": ["Bash(kubectl get *)", "Bash(kubectl describe *)"],
                                   "ask": ["Bash(./ops/release.sh *)"],
                                   "deny": ["Bash(kubectl delete *)", "Bash(dropdb *)"]}})


def grader(case, name):
    text = open(os.path.join(EVALS, case, "graders", name), encoding="utf-8").read()
    front = text.split("---")[1]
    get = lambda k: (re.search(r"^%s:\s*'?(.*?)'?\s*$" % k, front, re.M) or [None, None])[1]
    return get("type"), get("pattern") or get("input_match"), get("match") or "contains"


def script(name, *args, stdin=None, cwd=None):
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, name), *args], input=stdin,
                          capture_output=True, text=True, cwd=cwd).stdout


class Graders(unittest.TestCase):
    def outputs(self):
        labels = open(os.path.join(EVALS, "eval-judge-independent-calibrated", "prompt.md")).read()
        csv_text = labels.split("```csv")[1].split("```")[0].lstrip()
        ws = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, ws)
        shutil.copytree(os.path.join(EVALS, "eval-run-accounting", "resources", "eval-out"),
                        os.path.join(ws, "eval-out"))
        return {
            "eval-pass-k-floor": script("eval_stats.py", "floor", "--name", "never quotes a refund amount",
                                        "--results", "PPF"),
            "eval-judge-independent-calibrated": script("eval_stats.py", "calibrate", "--labels", "-", stdin=csv_text),
            "eval-run-accounting": script("eval_stats.py", "runs", "eval-out/result.json",
                                          "--fixture", "parse-invoices=resources/", cwd=ws),
            "verified-matches-plan": script("plan_conformance.py", "-", stdin=FIXTURE),
            "permission-profile-live": script("permissions_check.py", "--inline", "project=" + LIVE,
                                              "--command", "kubectl delete pod x"),
        }

    def test_regex_graders_pass_on_the_block_and_fail_on_prose(self):
        prose = open(os.path.join(HERE, "fixtures", "hybrid", "prose_only.md"), encoding="utf-8").read()
        outs = self.outputs()
        checked = 0
        for case, out in outs.items():
            for name in sorted(os.listdir(os.path.join(EVALS, case, "graders"))):
                kind, pat, match = grader(case, name)
                if kind != "regex" or not re.match(r"c\d[a-z]-", name):
                    continue
                hit_block, hit_prose = re.search(pat, out) is not None, re.search(pat, prose) is not None
                if match == "not_contains":
                    self.assertFalse(hit_block, (case, name))
                    self.assertTrue(re.search(pat, out.replace("VERIFIED: withheld", "VERIFIED: ok")), (case, name))
                else:
                    self.assertTrue(hit_block, (case, name, out))
                    self.assertFalse(hit_prose, (case, name))
                checked += 1
        self.assertEqual(checked, 15)  # 3 + 3 + 4 + 3 + 2 new regex graders: proves the loop ran

    def test_no_new_tool_used_graders(self):
        for case in self.outputs():
            for n in os.listdir(os.path.join(EVALS, case, "graders")):
                if re.match(r"c\d[a-z]-", n):
                    self.assertNotEqual(grader(case, n)[0], "tool_used", (case, n))


if __name__ == "__main__":
    unittest.main()
```
**Count check:** new regex graders are c1a, c1b, c1c (pass-k); c2a, c2b, c2c (calibrated); c2a, c2b, c2c, c2d (run-accounting); c4a, c4b, c4c (verified); c1a, c1b (permission). That is 15, matching `checked`. Step 5.5 re-counts it from the file listing.

`tests/fixtures/hybrid/prose_only.md`: a hand-written answer that is correct in prose and holds none of the fixed tokens. Example: "The safety rule failed one of three runs, so it is not reliable; the chance all three pass at that rate is low. The judge matched you on every pass but caught only one of three failures. The three parse-invoices runs never saw their files, so report them apart and re-run. Two changes fall outside the plan and README is missing, so it is not verified yet; you decide each. A deny anywhere beats an allow anywhere, even in your teammates' files."

- [ ] **Step 5.5: Run, expect red, then green.** Red before Step 5.3's files exist, green after, with `python3` and `/usr/bin/python3`. Reconcile `checked` with `ls evals/*/graders/c?[a-z]-*.md`. The controller runs the full suite after the merge.
- [ ] **Step 5.6: Commit** (`engineering-method evals: five cases graded by code first (tool ran + fixed lines), judge only for the residual` plus the Co-Authored-By line).

---

### Task 6: Whole-branch review (different model, executes)

- [ ] **Brief:** a fresh Fable 5.2 agent in its own read-only worktree gets this plan and `git diff fddb809...HEAD`, split if over about 60 KB. It must:
  - run the suite;
  - run each script on adversarial inputs: a compound deny with quotes, a trace with a list-typed `content`, a plan with `-` bullets inside a non-diff fence, a CSV with BOM;
  - check that every reference sentence's command actually runs as written from a scratch copy;
  - grep the diff for private names, product names, decision ids and emails;
  - check the fit with this plan's Out of scope;
  - report its model id.
- [ ] Each finding names its probe. Fix rounds: at most two. The re-review covers only the delta.

### Task 7: Evals (GATED: owner's yes on the count below)

Preconditions in the same pass:
```bash
date -u
[ -z "$ANTHROPIC_API_KEY" ] && echo ok-no-key
claude auth status | grep -E 'authMethod|subscriptionType'
```
Expected: no key, `claude.ai`.

**Checkouts outside home** (the sandbox cannot read `~/Documents`, and the eval uses the plugin folder in place, so both arms run from the scratchpad):
```bash
git worktree add --detach <scratch>/em-head-051 <branch head>
git worktree add --detach <scratch>/em-base-051 fddb809
B=<scratch>/em-base-051/plugins/engineering-method/evals
H=<scratch>/em-head-051/plugins/engineering-method/evals
for c in eval-pass-k-floor eval-judge-independent-calibrated eval-run-accounting verified-matches-plan permission-profile-live; do
  rm -rf "$B/$c" && cp -R "$H/$c" "$B/$c" && diff -r "$H/$c" "$B/$c" && echo "same: $c"
done
```
Expected: five `same:` lines. `rm -rf` first, so no 0.5.0 grader file survives a rename or delete on head. Then `git -C <scratch>/em-base-051 status --short` must list only those five folders, and `git -C <scratch>/em-base-051 diff --stat fddb809 -- plugins/engineering-method/skills plugins/engineering-method/scripts` must be empty.

**Command prefix, every eval command:** `CLAUDE_BIN=$(command -v claude)` once (read and shown), then `PATH=/usr/bin:/bin:/usr/sbin:/sbin "$CLAUDE_BIN" plugin eval …`, so the session's `python3` is `/usr/bin/python3` 3.9 outside home (Task 0).

**Two invocations, never mixed** (the Bash grant applies to every case in a run):
1. **Five target cases, Bash granted:**
   `PATH=/usr/bin:/bin:/usr/sbin:/sbin "$CLAUDE_BIN" plugin eval <checkout>/plugins/engineering-method --case '<one case>' --model opus --judge-model sonnet --ablation none -j 1 --runs 3 --threshold 0 --no-publish --trust-plugin --keep-temp --scaffold --allow-tools "Bash(python3 *)" --max-cost-usd <cap> --json <scratch>/eval-out/<dir>/result.json`. One case per command; `--scaffold` matters only for run-accounting.
2. **Regression cases, the 0.5.0 invocation unchanged, no Bash:** the same flags without `--allow-tools` and `--scaffold`.

The cap per command is runs × max($0.35, the case's measured cost per run) × 1.25, with `permission-profile-exploration-light` priced at $0.95 a run (its 0.5.0 head run stopped at its cost ceiling at $0.87-0.94 a run). A runner script refuses any command whose spent-so-far + cap passes the total cap, or whose sessions pass the total count, and logs each row before it starts (0.5.0 method).

**Order:**
- (a) **Smoke:** head, `--runs 1` on each of the five target cases (5 sessions). Read each answer and trace. Confirm the script ran and the block reached `last_message`; if not, apply F3 and re-smoke only the affected case.
- (b) **Gap:** base and head, 3 runs each, five cases (30).
- (c) **Regression, head only, 3 runs** (27), base reused from 0.5.0 head:
  - `eval-score-code-first`, `eval-metrics-report-only`, `eval-near-miss-unit-test` (h050);
  - `eval-plan-as-dataset`, `state-claim-measured`, `test-report-shows-evidence`, `stage-change-activation` (r050-head);
  - `verified-near-miss-no-plan` (h050);
  - `permission-profile-exploration-light`, whose 0.5.0 head run was partial (2 of 3), so it also gets a fresh base, 3 runs (+3).
  - Why these: they read the references this release edits (`behaviour-evals.md`, `measurement-and-state-claims.md`, `permission-profiles.md`), sit at the test stage whose cell and hook note change, or are the near-miss guards for behaviours 4 and 5. Cases that load none of the changed text reuse 0.5.0 unchanged.
- (c2) **The two near-miss guards again, with Bash granted:** `verified-near-miss-no-plan` and `permission-profile-exploration-light`, head only, 3 runs each, in the Bash-granted invocation (+6). Real users have Bash, and the new failure this release can cause, running `plan_conformance.py` on a throwaway script or `permissions_check.py` on a spike, is invisible without it. No new grader: read each kept trace for a Bash call naming either script. A call found is a hold.
- (d) **One contingency fix round:** head only on the five target cases (15), only if (b) shows a fault in the tool or the text, not a capability red.

**Reading results:**
- Report k of n per criterion beside each mean.
- For the five target cases, every new code grader is decided by construction on base (script-ran and content graders red, `c4c` green). Base versus head is read only on the `llm` graders and the unchanged graders, in a per-grader table that marks the by-construction cells. Case means are not compared across versions for these five.
- Read `tool_used` information (Bash calls in the trace) as a hint only: it counts denied and failed calls.
- New criteria are capability evals: below 2 of 3 on head is recorded as known red, not a hold.
- Regression criteria hold: an unexplained base-versus-head drop stops the release (principle 18).
- Read a sample of passing answers too, and read every run's `error` and the run-accounting traces (a run whose scaffold did not land is invalid, per the rule this release ships).

### Task 8: Release

- [ ] `plugins/engineering-method/.claude-plugin/plugin.json` and the `engineering-method` entry in `.claude-plugin/marketplace.json`: `0.5.0` → `0.5.1`. Plan-layer is untouched, so no plan-layer bump.
- [ ] `CHANGELOG.md` `## 0.5.1 — 2026-11-26` covers:
  - the hybrid approach in one paragraph (owner's intent: deterministic where possible, judge for the residual);
  - the three scripts and their blocks;
  - the routing fix (cell and hook note, measured word and character counts);
  - the five cases' grader changes, with base comparability stated: on base the new code graders are decided by construction, so base versus head is read only on the judged and unchanged graders;
  - that a correct prose-only answer without the tool's block now fails these criteria by design (the owner's intent);
  - the known issues: pass-k c1 strictness and the test-stage 0 reads closed; calibrated c2 and c3 **redefined, not closed**, since the prompt now supplies labels and the criteria test a different thing from the 0.5.0 wording;
  - the operator conditions for running these five cases: `--allow-tools "Bash(python3 *)"`, `--scaffold`, `PATH=/usr/bin:/bin:/usr/sbin:/sbin`, and a plugin copy outside the home folder;
  - results k of n base versus head;
  - sessions and the list-price estimate, billed to a claude.ai subscription (not spend);
  - the parked items.
- [ ] `evals/COVERAGE.md`: rows 126, 129, 135, 146, 149 lose their 0.5.0 known-issue notes and gain the new grader files and the 0.5.1 head k of n. Add rows for each new grader file, under the same G-ids.
- [ ] `README.md` (plugin): one short section "Scripts the skill runs", with the three commands, "they report, they never gate (exit 0 computed, 2 bad input)", Python 3.9 or later, and the four operator conditions above for the five eval cases (without them they score red). COVERAGE gets the same one-line note.
- [ ] Full suite once: `python3 -m unittest discover -s plugins/engineering-method/tests` → OK. Then run the repo's other two suites as CI does.
- [ ] Commit; push the branch; open the PR (body ends with the generated-with line); wait for the five CI checks:
  - release-gate unit tests;
  - `claude plugin validate --strict`;
  - versions agree / bumped;
  - private-identifier scan;
  - tests.

  Read each check's conclusion with `gh pr checks <n>`.
- [ ] Squash merge with `gh pr merge <n> --squash`. Then `git fetch && git log -1 origin/main`, and read the merged sha.
- [ ] Install: `claude plugin marketplace update ai-engineering-sdlc-tools && claude plugin update engineering-method@ai-engineering-sdlc-tools`. Read back the installed version from `claude plugin list` (expect `0.5.1`), and check the installed copy has `skills/engineering-method/scripts/eval_stats.py`. "Live" means this read-back, shown.

---

## Eval plan: session count and cost cap

| Step | Sessions | Basis |
|---|---|---|
| Task 0 probes, runs 1-2 (done) and run 3 (pending) | 3 | $0.36 measured for runs 1-2; run 3 about $0.25 |
| 7a smoke (head, 1 run × 5) | 5 | |
| 7b gap (5 cases × 3 runs × base and head) | 30 | |
| 7c regression (9 cases × 3 head) + fresh base for exploration-light (3) | 30 | |
| 7c2 the two guards with Bash (2 × 3 head) | 6 | plan review I8 |
| 7d contingency fix round (5 × 3 head) | 15 | only if needed |
| **Total ceiling** | **89** | inside the owner's 90; expected without 7d: 74 |

**Estimate:**
- Measured 0.5.0 costs per run: target cases 0.17-0.33 (mean 0.24), regression cases 0.12-0.45, `permission-profile-exploration-light` 0.87-0.94 (priced at 0.95).
- Expected without 7d about $25-27; with 7d about $30-31.
- **Hard cap for Task 7: $33 and 86 sessions**, enforced by the runner script. With the probes, the total stays inside the owner's $35 and 90 sessions.
- These are list-price estimates from the runner, judge calls included. Billing goes to the owner's claude.ai subscription (to be confirmed by `claude auth status` in the same pass). **Nothing runs without the owner's yes.**

## Self-review (done)

- **Plan review applied** (a different-model reviewer, verdict "ready after fixes"): I1 test fix; I2 run-accounting judge kept, narrowed; I3 one permission grader in place of two; I4 tolerant patterns; I5 CHECK lines; I6 run-3 probe (placeholder in Task 0); I7 base-comparison wording, `rm -rf` and `diff -r`; I8 tier-c scoping and the guards re-run with Bash; I9 the calibrated case redefined, said in the CHANGELOG. Minor 1-7 and 9 applied; minor 8 and the review's deferred items are listed under Out of scope.
- **Spec coverage:** the five behaviours map to Tasks 1-3 + 5. The routing gap maps to Task 4. Vendor checks are in the table above and in Task 0. TDD is in every script task. Headers are in Task 4's check. Eval cost is above. SDD lanes, release steps, Fit and Out of scope are present.
- **Placeholders:**
  - `<scratch>` and `<worktree>` are paths the controller fills.
  - `<cap>` is computed by the stated formula.
  - The `checked` count in Step 5.4 is re-counted from the files in Step 5.5.
- **Names agree across tasks:** `EVAL_STATS … v1`, `PLAN_CONFORMANCE v1`, `PERMISSIONS_CHECK v1`, and the grader patterns match the golden lines in Tasks 1-3.
