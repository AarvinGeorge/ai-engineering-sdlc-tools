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

## Root-cause investigation (0.4.0)

Each case also carries `skill-fired.md` (indicator only). `rc-03-full-input` copies its fixture into the workspace, so run it with `--scaffold`.

| Rule | Gap id | Grader (`<case>/graders/…`) |
|---|---|---|
| RC-1 Pin what ran: read revision, model id and model-shaping values for every instance, each with its command | G30 | `rc-01-pin-what-ran/graders/c1-pins-every-instance.md` |
| RC-1: do not rule a suspect in or out until its per-instance value is read; flag differing values as confounders | G30 | `rc-01-pin-what-ran/graders/c2-flags-differing-values.md` |
| RC-2 Read the decision record: the whole record for the event, the code's outcome kept apart from the model's | G31 | `rc-02-decision-record/graders/c1-code-outcome-apart-from-model.md` |
| RC-2: account for every number on the logged line by the part of the input it stands for | G31 | `rc-02-decision-record/graders/c2-maps-each-logged-size.md` |
| RC-3 Read the full input: name the cause from the complete model input, not a truncated local copy (runs need `--scaffold`) | G32 | `rc-03-full-input/graders/c1-names-empty-requester-role.md` |
| RC-3: check the truncation flag and match the copy's size to the original before naming a cause (`--scaffold`) | G32 | `rc-03-full-input/graders/c2-notices-truncation.md` |
| RC-3: a cause stated before the full input is read is a hypothesis; the final cause cites its store (`--scaffold`) | G32 | `rc-03-full-input/graders/c3-hypothesis-until-read.md` |
| RC-4 Quote the objection: the model's own stated reason, and a working run's reasoning to compare | G33 | `rc-04-objection/graders/c1-quotes-stated-reason.md` |
| RC-4: three separate statements, code decided, input said, model concluded, each with its source | G33 | `rc-04-objection/graders/c2-three-lines-apart.md` |
| RC-5 Diff the served inputs: block-by-block diff against each working population, from inputs as sent | G34 | `rc-05-diff/graders/c1-diffs-model-inputs.md` |
| RC-5: a flip on a supposedly identical input is a sign of a missing fact, not the cause. **Guard, not RC-5 proof**: 0.3.0 already passes it 2 of 3 | G34 | `rc-05-diff/graders/c2-flip-is-a-sign-not-cause.md` |
| RC-5: obtain the working run first and use it as the baseline before offering a cause | G34 | `rc-05-diff/graders/c3-working-run-first.md` |
| RC-6 Inventory the concept: list what already handles it, and extend it, before any remedy | G35 | `rc-06-inventory/graders/c1-inventory-before-remedy.md` |
| RC-6: deployed is not fired; check the ancestor and ask for evidence the path ran | G35 | `rc-06-inventory/graders/c2-deployed-is-not-fired.md` |
| RC-7 Trace the dropped fact: name the guard that drops a computed fact and confirm in the input as sent | G36 | `rc-07-trace-dropped-fact/graders/c1-names-the-guard.md` |
| RC-7: find the guard's history and pinning test; remedy changes that mechanism and its test | G36 | `rc-07-trace-dropped-fact/graders/c2-history-test-and-extend.md` |
| RC-8 Label the root, then fit the fix: every claim labelled measured, documented or hypothesis | G37 | `rc-08-label-and-fit/graders/c1-labels-and-records-hypothesis.md` |
| RC-8: a stopgap offered once, labelled, apart from the diagnosis | G37 | `rc-08-label-and-fit/graders/c2-stopgap-once-apart.md` |
| RC-8: ledger of rejected hypotheses with their refuting evidence; a count measures frequency, not cause | G37 | `rc-08-label-and-fit/graders/c3-ledger-and-variance.md` |
| RC-9 Close the loop: a per-stage table of conclusion, evidence, what was wrong and what unlocked the next stage | G38 | `rc-09-close-the-loop/graders/c1-stage-table.md` |
| RC-9: map each lesson to the step that would have caught it; record an uncovered one as a general entry in the method | G38 | `rc-09-close-the-loop/graders/c2-lessons-mapped-and-uncovered-recorded.md` |
| RC-10 Brief the investigator blind: no hypothesis in the brief, with the reason | G39 | `rc-10-blind-brief/graders/c1-withholds-hypothesis.md` |
| RC-10: the brief requires the full-input statement with its store, the model id and labelled claims | G39 | `rc-10-blind-brief/graders/c2-requires-input-line-and-model-id.md` |
| A debugging prompt loads the investigation reference (`tool_used: Read` on `root-cause-investigation.md`) | G40 | `rc-activation-loads-reference/graders/c1-reference-read.md` |
| A debugging prompt gathers the decision record and the model input as sent before any cause or fix | G40 | `rc-activation-loads-reference/graders/c2-evidence-before-fix.md` |
| Near miss: a plain rename does not load the reference. **Regression guard**, expected to pass on 0.3.0 and 0.4.0 | G41 | `rc-near-miss-rename/graders/c1-reference-not-read.md` |
| Near miss: the rename itself is done and shown. **Regression guard** | G41 | `rc-near-miss-rename/graders/c2-shows-renamed-function.md` |

## Rules added in 0.4.0

| Rule | Gap id | Grader (`<case>/graders/…`) |
|---|---|---|
| Instruction file compression: archive the whole file verbatim first and prove the copy equals HEAD | G42 | `instruction-file-compression/graders/c1-archive-verbatim-first.md` |
| Compression: sort sections by kind and treat each kind differently | G42 | `instruction-file-compression/graders/c2-classify-and-route.md` |
| Compression: every added claim carries its source; one-line rules kept as a grep checklist | G42 | `instruction-file-compression/graders/c3-new-claims-sourced-one-liners-kept.md` |
| Compression: a different-model reviewer diffs old against new before the commit | G42 | `instruction-file-compression/graders/c4-independent-diff-review.md` |
| Compression: the file states its own size rule; a secret and personal-data scan runs before the push | G42 | `instruction-file-compression/graders/c5-size-rule-and-push-scan.md` |
| Bounded fix loops: a stall (reopened finding, open count not falling) is named under a stated rule | G43 | `fix-loop-bounded/graders/c1-stall-named.md` |
| Bounded fix loops: stop dispatching at a stall; rule on or escalate the open findings | G43 | `fix-loop-bounded/graders/c2-stops-and-escalates.md` |
| Bounded fix loops: a five-round cap, what happens to findings open at the cap, per-round closed, reopened and open counts | G43 | `fix-loop-bounded/graders/c3-cap-and-ledger-counts.md` |

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
