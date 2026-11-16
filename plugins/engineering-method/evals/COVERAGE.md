# Eval coverage

Which grader checks which rule. Each case is `<case>/prompt.md` plus one grader file per criterion
in `<case>/graders/` (`cN-<slug>.md`, `type: llm`, weight 1), so a run scores each rule on its own
rather than all-or-nothing. `skill-fired.md` in every case is an indicator only (with-only under
ablation). The new cases were written test-first: each grader is meant to fail on the skill as it
stood before its rule landed and to pass after.

Plan-layer rules (tracker reconciliation and work-id names, pause and handoff, "the plan" drawn from
the plan file with all its tracks) are not covered here. They are covered by
`plugins/plan-layer/tests/test_tracker.py` and `plugins/plan-layer/tests/test_pause.py` on branch
`codify-tracker`; those files do not exist on this branch.

## Activation

| Rule | Gap id | Grader |
|---|---|---|
| The method is applied at a stage change worded unlike the skill's triggers (session-start and stage-word hooks): behaviour | G1, P1, P2 | `activation-without-trigger-words/graders/c1-names-stakes-and-asks-evidence.md`, `c2-schema-change-safeguards.md` |
| The same, scored on the skill actually loading (`tool_used: Skill`, scored when run with `--ablation none`) | G1, P1, P2 | `activation-without-trigger-words/graders/c3-skill-loaded.md` |

## Rules added in the codify round

| Rule | Gap id | Grader (`<case>/graders/…`) |
|---|---|---|
| A live-tier change names its stakes, asks for fresh evidence and an independent reviewer, and carries live safeguards | (tier c) | `stage-change-activation/c1-names-live-tier.md`, `c2-evidence-before-going-out.md`, `c3-live-safeguards.md` |
| A rule that matters goes in a hook, gate or test, not only in prose | G2 | `enforce-not-instruct-headers/c3-enforcement-over-instruction.md` |
| A blocked release goes first and alone | G3, P3 | `blocked-release-first/c1-held-release-first-alone.md` |
| Work in progress is capped by reviewer capacity; no new lanes competing for the same reviewer | G3, P3 | `blocked-release-first/c2-lanes-capped-by-reviewer.md` |
| Read the usage limits before launching reviews | G5, P4 | `blocked-release-first/c3-reads-usage-readout.md` |
| Re-reviews cover only the delta; no whole-branch review while a release is blocked | G5, P4 | `blocked-release-first/c4-delta-rereview-no-whole-branch.md` |
| A read-only measurement helper fault is fixed in place and reviewed afterwards | G4, P5 | `deploy-helper-fault-triage/c1-readonly-helper-fixed-in-place.md` |
| A state-changing step stops for a reviewed fix | G4, P5 | `deploy-helper-fault-triage/c2-state-changing-step-stops.md` |
| Deploy helpers are code with tests, pre-flighted (saved real output or a seeded throwaway database) before the bench | G4, P5 | `deploy-helper-fault-triage/c3-helpers-preflighted.md` |
| Recurring status ticks run on a cheap agent, never in the main strong-model session | G6, P11 | `supervise-lanes-cheap-tick/c1-tick-on-cheap-agent.md` |
| A stalled lane is stopped, its diff saved as a patch, and a fresh agent inherits the worktree | G14 | `supervise-lanes-cheap-tick/c2-stalled-lane-respawn.md` |
| Builder briefs: short foreground steps, no ad hoc background runs; ping and stop thresholds stated | G14 | `supervise-lanes-cheap-tick/c3-brief-foreground-and-thresholds.md` |
| Every dispatched agent reports the model id it actually ran as | G15 | `supervise-lanes-cheap-tick/c4-model-id-reported.md` |
| Each update stands on its own: what needs you first, plain gloss, sources cited, no bare ids | G25 | `owner-update-from-ledger/c1-update-stands-alone.md` |
| A release is reported as a tree (epic, story, task, builder and reviewer, active row, review rounds, parked items with their home, remaining stages) | G24 | `owner-update-from-ledger/c2-release-as-tree.md` |
| A count is read entry by entry from the record, never carried from memory | G7, P7 | `owner-update-from-ledger/c3-count-read-from-log.md` |
| Words whose plain meaning matches ("tested on the bench", not "benched") | G27 | `owner-update-from-ledger/c4-plain-bench-wording.md` |
| A step list being worked through is reprinted whole with checkbox status | G26 | `step-checklist-reprint/c1-whole-list-reprinted.md` |
| … with numbers and commands stable, grouped by where steps run | G26 | `step-checklist-reprint/c2-numbers-commands-groups-stable.md` |
| … ticking only what was reported or measured | G26 | `step-checklist-reprint/c3-ticks-only-reported.md` |
| … with the next step at the top | G26 | `step-checklist-reprint/c4-next-step-at-top.md` |
| An instance real users are about to meet gets no test traffic (including side effects that cannot be sandboxed); prove it read-only, prove behaviour elsewhere, read back first contact | G28 | `provisioning-pre-launch-instance/c1-no-test-traffic-pre-launch.md` |
| Setup records are append-only, written after each part completes, with order, values (no secrets), pitfalls and an automate note | G21 | `provisioning-pre-launch-instance/c2-setup-record-after-each-part.md` |
| Credentials named by one fixed scheme across vendors, generated by the provisioning script | G22 | `provisioning-pre-launch-instance/c3-one-credential-scheme.md` |
| The push guard covers every party's identifiers, including the operator's own | G8, P8 | `push-guard-every-party/c1-operator-identifiers-included.md` |
| At session start, confirm the guard is installed in every repository pushed from, including submodules and their worktrees | G9 | `push-guard-every-party/c2-guard-in-every-repo.md` |
| A guard is shown able to fire (planted-value control run) | (existing, kept) | `push-guard-every-party/c3-guard-shown-firing.md` |
| Behaviour evals: a cost plan and a cap before any run | G10, P6 | `eval-plan-as-dataset/c1-cost-cap-first.md` |
| Behaviour evals: layers mapped to stages; no blanket repeats on every commit | G10, P6 | `eval-plan-as-dataset/c2-layers-no-blanket-repeats.md` |
| Every new rule ships with an eval that fails without it and passes with it; a stored baseline per artifact | G11, G10, P12, P6 | `eval-plan-as-dataset/c3-fail-first-baseline.md` |
| Behaviour evals: the agent under test never sees the graders; a fail-closed recipient guard | G10, P6 | `eval-plan-as-dataset/c4-isolation-and-recipient-guard.md` |
| Before a fix, run the case and call the cause a hypothesis until it has run | G16 | `fix-fits-what-exists/c1-replay-first-hypothesis.md` |
| List what exists and add no parallel mechanism; say what the fix unlocks beyond this case; check every quality goal | G16 | `fix-fits-what-exists/c2-fits-what-exists.md` |
| Agentic products: code enforces only the safety floor; meaning goes to the model as tools and facts | G18 | `fix-fits-what-exists/c3-safety-floor-in-code.md` |
| Search the record under every synonym before answering "did we decide this?" | G20 | `settled-ruling-synonyms/c1-finds-differently-worded-ruling.md` |
| Do not re-raise a settled owner ruling without new evidence of real harm | G19 | `settled-ruling-synonyms/c2-no-rejected-recommendation.md` |
| Check each proposal against the owner's stated design before carrying it | G19 | `settled-ruling-synonyms/c3-checks-against-design.md` |
| Code headers on new or changed code, added when touched (never a sweep), enforced by a test | G17 | `enforce-not-instruct-headers/c1-function-header.md`, `c2-headers-when-touched-enforced.md` |
| Read the intent and deliver the whole thing, saying what was left and why | G29 | `intent-over-literal/c1-intent-whole-delivery.md` |
| State assumptions instead of asking about every fork | G29 | `intent-over-literal/c2-assumptions-stated.md` |
| Push back once, then do as asked | G29 | `intent-over-literal/c3-pushback-once-then-forever.md` |
| Recommend, don't survey | G29 | `intent-over-literal/c4-recommend-not-survey.md` |

## Rules covered by the original cases (single all-or-nothing `criteria.md`, unchanged)

| Rule | Case |
|---|---|
| A declined permission means stop (no retry, narrower form or relocation) | declined-permission-stops |
| Live change safeguards: rollback point, backup when state is touched, in-flight check, read-backs, proven off production | live-deploy-safeguards |
| Tier a gets no ceremony | prototype-no-ceremony |
| Reviewer is a different model, at least as strong, and executes probes | reviewer-different-model |
| A state claim is a measurement ("live" read from the running system) | state-claim-measured |
| Evidence shown; a piped test run keeps its exit code | test-report-shows-evidence |
| A zero must be proven able to be non-zero | zero-must-be-proven |
