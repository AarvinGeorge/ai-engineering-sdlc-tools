# Changelog

## 0.1.1 — 2026-10-15

**Tuning from the first eval run** (Sonnet, one run per arm: the skill fired in 1 of 7 cases).

- **Triggering.** The description now leads with the key use and names the moments that should
  fire it even when the question looks simple: "is it live / passed / zero?", status updates and
  test reports, deploy or restart steps on a live system, choosing or briefing a reviewer model, a
  declined permission, and planning or building code of any size. A `when_to_use` line lists the
  phrases. Description plus `when_to_use` is 1,253 characters (cap 1,536). A one-run check fired it
  in 6 of 7 cases.
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
