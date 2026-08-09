---
name: plan-layer
description: Use when a project has a plan/plan.json (or the user asks to start one, check plan drift, or update the planning page). Maintains shared state between the human and the coding agent - a JSON file rendered to a self-contained HTML page, with a gate that catches drift. Commands - /plan-layer init, status, check, render, help.
---

# plan-layer

A shared planning surface between a human developer and a coding agent.

**One file is the state.** `plan/plan.json` holds what is built, what is planned, what is
active right now, the deferred questions and the invariants. **A page is the view** —
`plan/index.html`, self-contained, generated, never hand-edited. **A gate catches drift.**
**Session hooks brief the agent** before the first word is typed.

The problem this solves: an agent's memory ends with its context window, and a human's
memory of what an agent did ends sooner than that. Written instructions get skipped.
So the state lives in a file both sides read, and the reading is automatic.

## Commands

| Invocation | Does |
|---|---|
| `/plan-layer init` | Create `plan/plan.json` from the template and render the first page |
| `/plan-layer status` | Print the current state — active item, stage, next up |
| `/plan-layer check` | Run the gate: structural failures and drift signals |
| `/plan-layer render` | Regenerate the page from the JSON |
| `/plan-layer help` | This document |

Scripts live at `${CLAUDE_PLUGIN_ROOT}/scripts/`. Run them with `python3`; they need
nothing installed.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/render.py"          # write the page
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/render.py" --check  # is the page stale?
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py"           # the gate
```

## init

1. Create `plan/` in the project root.
2. Copy `${CLAUDE_PLUGIN_ROOT}/templates/plan.json` to `plan/plan.json`.
3. Fill in `meta.project`, `meta.subtitle`, and `meta.updated` — **read the clock, do not
   recall a date.**
4. Replace the placeholder capability and next-item with real ones. Ask the user what the
   project is if it is not obvious from the repository.
5. Render, then run the gate.
6. Add `plan/index.html` to the repository — a generated file that is committed on purpose,
   so anyone can open the page without running anything.

## The cycle

Every unit of work moves through six stages. A stage is complete when its evidence exists,
not when it feels done. Each item in `plans.now` and `plans.next` carries a `stage`.

| Stage | Done when | If skipped |
|---|---|---|
| `intent` | The outcome is named — the outcome, not the method | Building something nobody asked for |
| `grounded` | Checked against the real system and measured; every claim has a source read in the same pass | Planning against how we *think* it works |
| `planned` | A plan document exists with verifiable steps and an explicit out-of-scope list | Scope creep, and no way to tell when it is finished |
| `building` | Steps executed one at a time, tree kept clean | — |
| `verified` | Gate green, evidence shown not asserted | A green result that tested nothing |
| `recorded` | Plan updated, page re-rendered, decisions logged | The next session re-derives what this one learned |

A project can define its own stages under `cycle.stages`. Omit the block to inherit these.

## Rules that make this work

**Update the plan during the work, not after it.** `plans.now[].stage` is meant to say
where the work actually is right now. A plan updated only at the end is a report.

**Never hand-edit `index.html`.** It is generated and will be overwritten. Edit the JSON.

**Finish every substantive turn by re-rendering and running the gate.** The page stamps a
fingerprint of the JSON, so a stale page announces itself instead of quietly showing old
data.

**Evidence, not assertion.** A capability with `build` set to anything but `not-started`
must carry `evidence`. The gate enforces this, because progress claimed without evidence is
the shape of a comfortable lie.

**Parked is not dropped.** A question deferred goes in `parked` with a `trigger` naming when
it must be answered.

## What the gate checks

`check.py` separates two kinds of problem:

- **FAIL** — structural. A capability claiming progress with no evidence; an item past
  `planned` with no `plan_file`; an invariant in an unknown state; the page out of sync with
  the JSON; `plan_version` disagreeing with the newest changelog entry. Exit code 1.
- **DRIFT** — heuristic. Uncommitted work outside the plan directory while the plan sits
  untouched; the last substantive commit newer than `meta.updated`; a plan older than
  fourteen days. Exit 0 unless `--strict`.

**It deliberately does not check whether the plan is true.** No script can. It makes
*forgetting* visible; judging accuracy stays with the `grounded` and `verified` stages.

## Diagrams

The engine ships none — diagrams are about one project's specific mechanism and do not
generalise. A project that wants them creates `plan/figures.py` exposing:

```python
CSS = """
  .my-box{fill:none;stroke:var(--line)}
"""

def build(data):     # data is the parsed plan.json
    return "<figure>…</figure>"   # any HTML; inline SVG works well
```

**A figure must ship its own CSS.** An SVG `<rect>` with no fill rule renders solid black
with invisible text — a missing stylesheet looks like a broken page, not a plain one. The
module-level `CSS` string is appended to the page stylesheet, so it can use the theme tokens
(`--ink`, `--line`, `--accent`, `--done`, `--gap`) and work in both themes.

The renderer picks the module up automatically and skips the section if it is absent or
raises.

## Configuration

Optional `.plan-layer.json` in the project root:

```json
{ "plan_dir": "plan", "plan_file": "plan.json", "page_file": "index.html" }
```

## Publishing the page

`plan/index.html` is fully self-contained — no scripts, no fonts, no external requests. Open
it locally, host it anywhere, or publish it as an artifact so the human can read it without
a terminal.
