---
name: plan-layer
description: Use when a project has a plan/plan.json (or the user asks to start one, check plan drift, or update the planning page). Maintains shared state between the human and the coding agent - a JSON file rendered to a self-contained HTML page, with a gate that catches drift. Commands - /plan-layer init [--light], status, check, render, sync, help.
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

**Works with `engineering-method` (optional).** That sibling plugin carries the engineering
method; this one only keeps the state. Neither needs the other.

## Light vs full — when

- **Light** (`meta.mode: "light"`, `init --light`): a short project — a one-week take-home, a
  spike, a small app. You get the state file, the page and the gate's self-consistency FAILs, without the
  figures, archive or rolling ceremony: no figure or roll-due signals, and `sync.py` never rolls.
  **Archify views are opt-in in both modes:** a light plan that declares `views` gets them checked
  exactly as in full mode (missing spec, stale spec sha, live-revision drift); one that declares
  none is held to nothing about views.
- **Full** (the default; `meta.mode` absent or `"full"`): a project that runs for weeks, has a
  deployed system, drawings beside the page, or history worth archiving.
- Switch by changing the one field. A light plan that outgrows itself becomes full with no
  migration; every plan written before 0.16.0 is full and unchanged.

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

**Commit `plan/archive/` with `plan.json` and `index.html`.** Since 0.16.0 `sync.py` writes
`plan/archive/*.json` whenever it rolls, so the three move together in one commit — a plan
committed without its archive has lost the records it rolled.

## The conventions that keep it readable

These are not style preferences. Each one is what a reader needs in order to answer a
question in a single glance, and most are now checked.

**One item in `plans.now` at a time.** Its `tasks` list is the visible checklist, and that
pair answers "what is happening right now" without the reader choosing between candidates.
The gate **fails** on a second active item. A project that genuinely runs several streams
says so with `meta.allow_multiple_active: true` rather than by accident.

**A checklist someone has to EXECUTE declares columns.** A manual pass, an acceptance run, a
migration rehearsal: steps like these carry instructions, not just a name. Put them in
`task_columns` on the item and the same keys on each task, and the page renders one row per
step instead of a name with a paragraph under it, which is the difference between a page
somebody works from and a page they abandon for the plan document.

```json
"task_columns": [
  { "key": "tests", "label": "What we are testing for" },
  { "key": "from",  "label": "From" },
  { "key": "send",  "label": "Send" },
  { "key": "pass",  "label": "Pass when" },
  { "key": "how",   "label": "How to do it" }
],
"tasks": [
  { "name": "7 book two named people at once", "state": "todo",
    "tests": "two names resolve in one request", "from": "the executive seat",
    "send": "Book a call with Alex and Priya on Tuesday",
    "pass": "both guests are on the event", "how": "reply in the same thread" }
]
```

A key may not be `name`, `state` or `note`, and may not repeat; the gate **fails** on either,
and on a column with no key or no label. A step still to run that leaves a declared column
empty **drifts**, because it cannot be executed from the page. A done step is exempt. `note`
keeps working and renders as a full-width line under its own row, which is where the evidence
that a step passed belongs. Leave `task_columns` off for an ordinary checklist: without it the
list is exactly what it has always been.

**Say how a step turned out, not only where it is.** `state` is position in the run; `result`
is the outcome, and a step can be `done` and have failed. Where any step in an item carries
`result`, the table gains a leading `Result` column, because a run is read to find out how it
went. `pass`, `fail`, `covered` and `blocked` are styled, each with a word and a mark so they
stay separable on a phone and in either theme; any other word renders as written. The gate
**fails** on a result that is not a word.

**A note may be a list.** Written as points it reads faster than one dense sentence, typically
the time the step ran and then what happened. A string still renders exactly as it always did.
The gate **fails** on a note that is neither prose nor a list of points.

```json
{ "name": "2 move it, in the same thread", "state": "done", "result": "pass",
  "note": ["PASS 13 Sep 17:04 UTC", "the right meeting moved and nothing was asked"] }
```

**A finished item leaves `now` for `done`, and gains two fields.** A `period` saying when the
work ran, and an `outcome` saying what it produced. Move the item rather than rewriting it;
the page reads the carried-over `status` in the outcome slot and `plan_file` in the `file`
slot, so nothing is lost on the way. Both missing fields **drift**.

**Archive rather than accumulate.** When completed plans or closed edge cases get long, keep
the recent ones in full, condense the rest to a line each, and move their full text to a
sibling markdown file next to `plan.json`. Say where it went in that section's heading hint,
so a reader who wants the history knows it exists:

```json
"headings": {
  "done": ["Plans completed", "the six most recent in full; the older ones are in plan/completed_archive.md"]
}
```

**Section headings are data.** `meta.headings` overrides any section's title and hint. The
hint is the right place to say what a section is carrying today, which is how a long page
stays honest about what it is showing and what it is holding back.

**Figures derive everything from the plan.** Numbers come from `facts`, and a status shown in
a drawing comes from the capability, invariant or item it describes. A figure that hardcodes
either will disagree with the table above it, and the drawing is the half nobody re-reads.

**Look at a figure you changed.**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/figcheck.py"
```

It writes each figure to `plan/.figures/` as its own page and screenshots it, and **fails** on
a label that crosses the right edge or two labels printing over each other. Then open the
screenshots and read them. Reasoning about coordinates is not looking, and both of those
faults have shipped in a figure that had already been read carefully.

**The page prints a key.** Every status label on it is generated from the same tables the
sections render from, so a marker cannot appear in one place and mean something else in
another. Nothing to maintain; worth knowing it is there before inventing a new vocabulary.

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
| `/plan-layer init --light` | The same from the minimal light template (`templates/plan.light.json`) |
| `/plan-layer status` | Print the current state — active item, stage, next up |
| `/plan-layer check` | Run the gate: structural failures and drift signals |
| `/plan-layer render` | Regenerate the page from the JSON |
| `/plan-layer sync` | After ANY change: roll aged records into `plan/archive/` (lossless; `--no-roll` opts out), refresh view facts from disk, render, run the gate — the one command. `--live-revision <sha>` at the end of a deploy |
| `/plan-layer roll` | Move aged records into `plan/archive/` in full by hand — `sync` already does this; use `roll --dry-run` to preview |
| `/plan-layer help` | This document |

Scripts live at `${CLAUDE_PLUGIN_ROOT}/scripts/`. Run them with `python3`; they need
nothing installed.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/render.py"          # write the page
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/render.py" --check  # is the page stale?
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py"           # the gate
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/figcheck.py"        # look at the figures
```

## init

1. Create `plan/` in the project root.
2. Copy `${CLAUDE_PLUGIN_ROOT}/templates/plan.json` to `plan/plan.json` — or, for
   `init --light`, `templates/plan.light.json` (see "Light vs full"; then skip steps 7 and 8).
3. Fill in `meta.project`, `meta.subtitle`, and `meta.updated` — **read the clock, do not
   recall a date.**
4. Replace the placeholder capability and next-item with real ones. Ask the user what the
   project is if it is not obvious from the repository.
5. Render, then run the gate.
6. Add `plan/index.html` to the repository — a generated file that is committed on purpose,
   so anyone can open the page without running anything.
7. Copy `${CLAUDE_PLUGIN_ROOT}/templates/MAP.md` to `plan/MAP.md`: the map a fresh session
   reads first — what lives where, the commands after any change, and the reading rules that
   keep token use down.
8. Optional, if the project keeps drawings beside the page: create `plan/archify/` and copy
   `${CLAUDE_PLUGIN_ROOT}/templates/topology.architecture.json` as the first spec, filling in
   `meta.repository.url` and `revision` from the project's own repository. See "Drawings beside
   the page" below.

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

**The front page shows this month.** `sync.py` rolls automatically (0.16.0): it moves older done items, old changelog entries and the queue beyond the
first eight into `plan/archive/*.json` in full (nothing deleted), keeping one queued item per
capability, and prints what moved. The page then says "N older in archive/…" from the file itself, never from typed
text. Never load `plan.json` whole into context and never hand it to a subagent; edit by key.

**Drawings beside the page (views).** Some drawings cannot live on the page — an interactive one
with its own scripts and stylesheet. Keep them beside it and let the gate keep them honest:

1. The spec is the truth and is committed (`plan/archify/<name>.<type>.json`); the delivered HTML
   is regenerable and ignored; the published URL is the durable pointer.
2. `plan.json` `views[]` lists each: `figure` (which page figure it belongs under), `label`,
   `spec`, `url`. Never type `spec_sha256` or `revision`; `sync.py` writes them from the files.
3. Every deploy ends with `sync.py --live-revision <sha read off the running system>`. The gate
   then reports a drawing measured at an older commit as DRIFT until it is re-checked.
4. The tested companion is **Archify** (`npx skills add tt-a1i/archify -g`, MIT). Use ITS
   primitives, do not reinvent them: `meta.repository.revision` + `components[].sources` for
   "measured, not described" (verified with `validate --repo-root`), `compare` for a before/after
   in a plan document, the delivery receipt's SHA-256 for "which spec produced this page". It is
   installed separately so it updates on its own; this plugin never bundles it. Its exported SVG
   carries its own stylesheet and font (tested 27 Sep 2026), so the page LINKS a view, never
   embeds it.

**Parked is not dropped.** A question deferred goes in `parked` with a `trigger` naming when
it must be answered.

## What the gate checks

`check.py` separates two kinds of problem:

- **FAIL** — structural. A capability claiming progress with no evidence; an item past
  `planned` with no `plan_file`; a task state outside the four; an invariant in an unknown
  state; a parked question with no trigger; an `accepted` edge case with no reasoning; two
  items claiming one plan document; duplicate capability ids; a second item in `plans.now`;
  `meta.updated` in the future; the page out of sync with the JSON; `plan_version`
  disagreeing with the newest changelog entry; an unknown `meta.mode`; a `meta.size_budget_kb`
  that is not a positive whole number. Exit code 1.
- **DRIFT** — heuristic. Uncommitted work outside the plan directory while the plan sits
  untouched; the last substantive commit newer than `meta.updated`; a plan older than
  fourteen days; a finished plan with no period or no outcome; `meta.version` disagreeing
  with `plan_version`; an item naming no capability; assertions declared but never verified,
  or verified over a week ago; a figure reading a fact the plan does not define; an active
  item where every unfinished task is blocked; records due to roll; `plan.json` over its size
  budget (`meta.size_budget_kb`, default 200 KB). Exit 0 unless `--strict`.
- **Light mode** skips the full-only signals: figures and roll-due. Declared views are checked
  in both modes. Every FAIL above still applies.

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

In `plan.json` itself: `meta.mode` (`"full"` or `"light"`) and `meta.size_budget_kb` (the KB
size above which the gate drifts; default 200).

## Publishing the page

`plan/index.html` is fully self-contained — no scripts, no fonts, no external requests. Open
it locally, host it anywhere, or publish it as an artifact so the human can read it without
a terminal.
