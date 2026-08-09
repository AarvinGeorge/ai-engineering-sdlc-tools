# plan-layer

A shared planning surface between a human developer and a coding agent.

**One JSON file is the state.** **A self-contained HTML page is the view.** **A gate catches
drift.** **Session hooks brief the agent before the first word is typed.**

## The problem

An agent's memory ends with its context window. A human's memory of what the agent did ends
sooner than that. The usual fix is to write "always update the plan" into an instructions
file — but instructions get skipped, especially by a fresh session that has not read far
enough to know the instruction exists.

So this puts the state in a file both sides read, and makes the reading automatic.

## Install

```bash
claude plugin marketplace add AarvinGeorge/ai-engineering-sdlc-tools
claude plugin install plan-layer@ai-engineering-sdlc-tools
```

Then, in any project you want it for, ask the agent to run `/plan-layer init`.

**Nothing to install beyond Python 3**, which macOS and most Linux ship. Zero third-party
packages, by design.

## What you get

```
your-project/
  plan/
    plan.json      the state — you and the agent both edit this
    index.html     the view — generated, committed, never hand-edited
    figures.py     optional: your own diagrams
```

- **`plan.json`** holds what is built, what is planned, what is active right now, the
  questions deferred by decision, and the invariants that must not break.
- **`index.html`** is fully self-contained: no scripts, no fonts, no network requests. Open
  it locally, host it anywhere, or publish it so the human can read it without a terminal.
  It carries a fingerprint of the JSON, so a stale page says so instead of quietly showing
  old data.

## The cycle

Every unit of work moves through six stages, and each item on the plan carries the one it is
in. Each stage names **what "done" means** and — more usefully — **what it looks like when
skipped**.

| Stage | Done when | If skipped |
|---|---|---|
| Intent | The outcome is named — the outcome, not the method | Building something nobody asked for |
| Grounded | Checked against the real system and measured | Planning against how we *think* it works |
| Planned | A plan document exists with verifiable steps and an out-of-scope list | Scope creep, and no way to tell when it is finished |
| Building | Steps executed one at a time, tree kept clean | — |
| Verified | Gate green, evidence shown not asserted | A green result that tested nothing |
| Recorded | Plan updated, page re-rendered, decisions logged | The next session re-derives what this one learned |

Define your own under `cycle.stages`, or omit the block to inherit these.

## The gate

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py"
```

Two kinds of finding, kept separate on purpose:

- **FAIL** — structural. A capability claiming progress with no evidence. An item past
  *planned* with no plan document. An invariant in an unknown state. The page out of sync
  with the JSON. Exit code 1.
- **DRIFT** — heuristic. Uncommitted work outside the plan directory while the plan sits
  untouched. The last substantive commit newer than the plan's timestamp. A plan nobody has
  touched in a fortnight. Exit 0 unless `--strict`.

**It deliberately does not check whether the plan is true.** No script can. It makes
*forgetting* visible; judging accuracy stays a human and agent job.

## The hooks

| Event | What happens |
|---|---|
| `SessionStart` | Current state — active item and stage, next up, failing invariants, gate results — is injected before the agent's first word |
| `PreCompact` | Fires when context is about to be summarised away, which is when working state gets lost. Flush to the plan first |

Both are **silent in projects with no plan file**, and both **fail open** — a broken
briefing never blocks a session.

## Your own diagrams

The engine ships none: diagrams are about one project's specific mechanism and do not
generalise. To add your own, create `plan/figures.py`:

```python
def build(data):                  # data is the parsed plan.json
    return "<figure>…</figure>"   # any HTML; inline SVG works well
```

The renderer picks it up automatically, and skips the section if it is missing or raises —
a broken figure never costs you the page.

## Configuration

Optional `.plan-layer.json` in the project root, if the defaults do not suit:

```json
{ "plan_dir": "plan", "plan_file": "plan.json", "page_file": "index.html" }
```

## Schema

[`schema/plan.schema.json`](schema/plan.schema.json) documents every field. **Every section
is optional** — a project that fills in only `plans` gets a page with only plans on it, and
nothing looks broken.

## Licence

MIT.
