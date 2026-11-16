# Changelog

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
