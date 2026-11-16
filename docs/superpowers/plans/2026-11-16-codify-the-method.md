# Plan: codify the method so it runs without reminding (16 Nov 2026)

Tier **b (internal)**. Branch `sdlc-codify-2026-11-16` off `main` (876cfe3). No push, no PR, no publish.

## Goal
Lessons from a long-running live project become general practice in the marketplace, and the method
fires by itself at startup, after `/clear` and compaction, and at each stage change.

## Done means
1. Activation without reminding (startup, clear, compact, stage change).
2. Every lesson is a general rule in the right plugin, extending what exists, each with an eval.
3. plan-layer owns the external-tracker mirror (Notion first, adapters for others); engineering-method says when the record moves.
4. Nothing project-specific ships (local identifier scan, list kept outside the repo).

## Vendor facts (hooks reference, code.claude.com/docs/en/hooks.md, read 16 Nov 2026)
- SessionStart `source` is startup | resume | clear | compact; `hookSpecificOutput.additionalContext` is injected.
- UserPromptSubmit receives `prompt`; it has no matcher (the script filters); additionalContext is injected.
- PreCompact stdout steers the summary only; re-briefing after compaction is SessionStart `compact`.
- Output cap 10,000 characters.

## Lanes (one writer per worktree)
| Lane | Worktree branch | Builder | Scope | Capability |
|---|---|---|---|---|
| A hooks | `codify-hooks` | Sonnet | EM `hooks/hooks.json`, `scripts/method_hook.py`, `tests/`, CI step | NEW (EM has no hooks; reuses PL's brief.py pattern) |
| B text | `codify-text` | Opus | EM `SKILL.md`, all `references/`, new `references/behaviour-evals.md`, README | EXTEND (one NEW reference: no eval guidance exists) |
| C plan-layer | `codify-tracker` | Sonnet | PL tracker mirror + adapters, `pause`, SKILL text | EXTEND (sync, brief, check) |
| D evals | `codify-evals` | Opus | new EM eval cases, written before lane B | EXTEND `evals/` |

Order: A, C, D start together; base evals run on D's cases (RED); then B; reviews per lane by Fable 5.2
with probes; merge; versions; full suites; head evals (GREEN); fresh-session hook scenarios; identifier scan; whole-branch delta review.

## Stage map (shared by lane A's hook and lane B's SKILL.md table)
| Stage | Words | Skill | Reference |
|---|---|---|---|
| plan | plan, design, spec | superpowers:writing-plans | docs-and-decisions.md, parallel-and-worktrees.md |
| build | build, implement, fix, refactor | superpowers:test-driven-development | model-routing-and-cost.md, parallel-and-worktrees.md |
| review | review | superpowers:requesting-code-review | review-loop.md |
| test | test, bench, eval, verify | superpowers:verification-before-completion | measurement-and-state-claims.md, behaviour-evals.md |
| deploy | deploy, rollout, rollback, restart, migrate | — | live-system-changes.md |
| merge | merge, push | superpowers:finishing-a-development-branch | live-system-changes.md |
| release | release, promote, ship | — | live-system-changes.md, progress-ladder.md |
| report | status, progress, report | — | progress-ladder.md, measurement-and-state-claims.md |

## Out of scope
- work-log changes (no lesson maps there).
- A tracker adapter that calls a tracker API directly (the agent reads/writes via the tracker's connector; plan-layer computes expected vs actual).
- New ideas: parked in the source proposal file, not built.

## Lesson map
Private working file (not shipped). Gaps G1–G29 and proposal items P1–P12 are each assigned to a lane above.
