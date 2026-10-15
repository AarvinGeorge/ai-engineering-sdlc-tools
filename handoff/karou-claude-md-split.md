# Karou `agent/CLAUDE.md` §5-§7: where each rule goes (input for a later slimming; nothing edited)

Legend: **SKILL** = now carried by `engineering-method` (the Karou file can point to it) ·
**KAROU** = project-specific, stays · **DROP** = stale or superseded.

## §5 Claude's role
- Role list (seven hats) — KAROU (project persona).
- "Retained from parent: product/commercial lens" — KAROU.
- Superpowers skills table — SKILL (§3 pointer table supersedes it; keep the version note only if wanted).
- Model selection 2026-09-17 block ("SUPERSEDED" header + table) — DROP (kept "for reasoning"; the reasoning now lives in references/model-routing-and-cost.md).
- Model selection 2026-09-24 table (Fable/Sonnet/Haiku) — SKILL (generalised as strongest/mid/small); KAROU keeps one line naming which concrete model fills each tier.
- Reviewer always a different model, at least as strong — SKILL (principle 10, review-loop.md).
- Final whole-branch pass is Fable by founder's choice — KAROU (a project choice; the skill states the general caveat).
- Every reviewer must execute — SKILL.
- Not Fable for planning documents — SKILL (model-routing rule 5, generalised).
- Evidence behind the change (24 Sep Sonnet episode) — DROP (history; the lesson is in the skill; the decision log keeps the record).
- Token discipline (brief never corpus, implementers never run full suite, bound turns) — SKILL.
- Three override rules (turn count, escalate on failure, model does not fix independence) — SKILL.
- Always name the model when dispatching — SKILL.
- One writer per worktree — SKILL (parallel-and-worktrees.md).
- Parallel versus serial test and table — SKILL.
- "Fable's jobs, now that it is back" — DROP (superseded by the 24 Sep block).
- Cost rule (context × turns) — SKILL.
- Subagent authorization (2026-07-28) — KAROU (a standing per-project grant; could also move to the global file if wanted everywhere).

## §6 Working agreement
- Intent-driven development bullets (read intent, state assumptions, deliver whole, recommend, evidence) — SKILL in part (evidence, recommend); KAROU for "intent-driven" framing unless moved to global.
- Vendor docs before vendor claims — SKILL (principle 3); KAROU keeps the LangSmith example only.
- A state claim is a measurement — SKILL.
- Step by step / wait for green light — KAROU (founder's working style; candidate for global).
- Push back when warranted — DROP here (already in global §4).
- No over-engineering (three tests, switch, cuts the other way) — SKILL; the tier 0/1 vs tier 2 wording — KAROU.
- Folder organisation and document headers — SKILL (docs-and-decisions.md); KAROU keeps its concrete folder names.
- Usage discipline (six rules) — SKILL (model-routing-and-cost.md, review-loop.md fix rounds); the $1,160 incident note — DROP to decision log.
- The development loop (six stages) — SKILL in part (record as you go, plans before building); the plan-layer machinery and sync.py commands — KAROU (and the plan-layer plugin).
- Figures on the planning page rule — KAROU (plan-layer specific).
- Response conventions: header + timestamp — DROP here (global §1 carries it).
- Simple language, short, bullets, don't ask downstream questions — DROP here (global §4).
- Take the heavy lifting — KAROU (candidate for global).
- Wait for the green light — KAROU.
- Progress ladder — SKILL (progress-ladder.md); KAROU footer names (staging/production) stay as the project's footer lines.

## §7 Production server
- "Since 15 Oct: production = container stack…" — KAROU.
- Never run tests inside a live container — SKILL (live-system-changes.md) + KAROU names.
- Read-only by default / ask before mutating / never restart blind / no secrets / back up / prove before production — SKILL (general rules); KAROU keeps the unattended-upgrades note and the bench pointer.
- Access commands (ssh, users, paths) — KAROU.
