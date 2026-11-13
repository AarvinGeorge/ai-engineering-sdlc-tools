# Changelog

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
