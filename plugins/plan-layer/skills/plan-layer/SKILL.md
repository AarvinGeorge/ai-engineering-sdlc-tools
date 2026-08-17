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

## The standing job — keep it true, every turn

This is not a document written at the end. It is the shared state, and it is the agent's job
to keep it accurate as the work happens. The human should never have to say "the page is out
of date."

**Every turn that changes anything, before finishing:**

1. **Ask where the work actually is now.** A task finished? An item finished? Something
   learned that changes a plan? Something found that belongs on the record?
2. **Make the smallest edit that makes the page true.** Change the fields that moved. Do not
   rewrite sections that did not change, and do not restructure because it would read better
   — churn destroys the reader's sense of what is new.
3. **Move items rather than duplicating them.** A finished item leaves `now` for `done`, and
   something from `next` takes its place. An item's own `tasks` list is the first thing to
   update, because the gate reads it.
4. **Re-render, run the gate, republish.**

**What "true" means here is specific:** the page must not disagree with itself. If an item's
tasks say the work is done, its status must not say it is waiting to start. If an active item
works on a capability, that capability cannot read as untouched. The gate **fails** on these,
so a turn cannot end on a page that contradicts itself.

### Say what waits on what

When one piece of work cannot start until another finishes, record it:

```json
{ "name": "Screening", "blocked_by": ["Containment"], ... }
```

**Do not leave it in prose.** A dependency described in a plan document, or explained in
conversation, exists nowhere a check can see it — and that is exactly how an item stays marked
active for days while the thing it waits on sits unstarted at the bottom of the queue. The gate
now fails when an active item waits on something that is only queued, because one of the two is
in the wrong place.

## Who the page is for

**A person who has never seen the project, reading it cold, should understand what is
happening and why.** That is the point of the page. It is not a status file for people who
already know the answer.

That property decays every time someone who knows the context writes a sentence. So:

- **Plain language, full substance.** Simplify the wording, never drop the information.
  Explaining something clearly is not dumbing it down.
- **No shorthand a stranger cannot resolve.** No "as discussed", no in-jokes, no phrase that
  only makes sense to someone who was in the conversation. The gate **fails** on these.
- **Spell out cross-references.** "Depends on P1" means nothing to a new reader; say what P1
  is. The gate **drifts** on bare references.
- **Define terms or do not use them.** Capitalised jargon with no glossary entry drifts.
- **One idea per paragraph.** A paragraph doing three jobs is how a good page becomes an
  unreadable one.

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

**The gate runs itself at the end of every turn** via a Stop hook, and blocks on FAIL. You
still re-render after editing the plan — the hook will tell you if you forgot, but finding
out at the end of the turn is slower than doing it as you go.

**Finish every substantive turn by re-rendering and running the gate.** The page stamps a
fingerprint of the JSON, so a stale page announces itself instead of quietly showing old
data.

**Evidence, not assertion.** A capability with `build` set to anything but `not-started`
must carry `evidence`. The gate enforces this, because progress claimed without evidence is
the shape of a comfortable lie.

**Link every plan item to a capability.** `"capability": <id>` on items in `plans.now` and
`plans.next`. It is what lets a reader reconcile the plan lists with the capabilities table,
and the gate checks it. Capabilities may carry a `short` label for figures.

**Numbers quoted in two places belong in `facts`.** Figures read `data["facts"]` instead of
restating a value that also appears in the prose.

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

## Assertions — the plan checking itself

The gate checks consistency. `--verify` checks truth, if the plan declares how:
`assertions_setup` gathers facts once into `$PLAN_FACTS`, and each entry in
`assertions` reads from it and compares against `expect`.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" --verify
```

**Never run these from a hook or without being asked.** They are shell commands from
a repository file. Explicit human request only.

**Write them as one gather, many checks.** Separate connections per assertion are
slow and can trip a host's rate limiting. Keep the remote command trivial and match
locally; a check that errors looks identical to a claim that is false.

**When an assertion mismatches, check the command before changing the claim.** Most
early mismatches are quoting, not drift.

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
