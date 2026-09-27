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
    MAP.md         the map a fresh session reads first: what lives where, the commands, the reading rules
    archive/       history in full, machine-readable: older done items, old changelog, the queue beyond the front page
```

- **`plan.json`** holds what is built, what is planned, what is active right now, the
  questions deferred by decision, and the invariants that must not break.
- **`index.html`** is fully self-contained: no scripts, no fonts, no network requests. Open
  it locally, host it anywhere, or publish it so the human can read it without a terminal.
  It carries a fingerprint of the JSON, so a stale page says so instead of quietly showing
  old data. Light and dark both meet **WCAG AA** on every text token, asserted by a test
  rather than judged by eye. It opens with a **key** listing every status label it uses,
  generated from the same tables the sections render from — so a marker cannot appear on the
  page without appearing in the key, and cannot mean one thing in a table and another in a
  card. A pulsing dot marks whatever is in progress right now, and stops pulsing (keeping its
  colour) when the reader prefers reduced motion.
- **The front page shows this month.** (0.14.0) A page that carries every completed item and
  every changelog entry since the project began stops being read. `scripts/roll.py` moves
  older records into `plan/archive/*.json` **in full** — the last 8 done items, the last 10
  changelog entries and the first 8 queued items stay, plus one queued item per capability so
  the gate never reads "blocked with nothing queued" because of a roll. Nothing is deleted;
  running it twice is safe. The gate says when it is due, and the Done and Next headings gain
  "N older in archive/…" counted from the archive file, never typed. Keep-counts are
  overridable per project under `roll` in `.plan-layer.json`.
- **Views** (0.15.0) are drawings that live beside the page rather than on it — the first kind is
  Archify, whose exported SVG carries its own 132 KB stylesheet and font. `plan.json` `views[]`
  lists each one: the spec in the repository (the truth), the published URL (the pointer), and two
  facts written only by `scripts/sync.py`, never typed: the spec's SHA-256 and the commit it was
  measured at (`meta.repository.revision`). The gate says when a drawing has gone stale: the spec
  changed since delivery, the live revision moved past it, or the spec is missing.
- **`MAP.md`** is copied on init: a one-page map of the folder for the agent, with the
  reading rules that keep token use down — edit `plan.json` by key with a script, read one
  figure by function name, never hand the file to a subagent.

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

## Keeping the page one argument

An item under Active or Next may name the capability it serves:

```json
{ "name": "Tenant identity in traces", "capability": 6, "stage": "intent", … }
```

It renders as a chip beside the item, and the gate checks it: a reference to a capability
that does not exist **fails**; an item that names none **drifts**. Without the link, the plan
lists and the capabilities table are two documents that happen to share a page.

## Showing the plan, not just its filename

An active item that only points at a plan document tells the reader "a plan exists, here is a
file you cannot open." Give it a checklist:

```json
{
  "name": "Email channel",
  "stage": "building",
  "plan_file": "13_email_channel.md",
  "tasks": [
    { "name": "Prove the round trip", "state": "done", "note": "the door is fire-and-forget" },
    { "name": "Build the adapter",    "state": "blocked", "note": "needs the Google project" },
    { "name": "Trust tiers",          "state": "todo" }
  ]
}
```

It renders as a numbered checklist with a count. `state` is one of `done`, `active`, `todo`,
`blocked`, and the gate **fails** on anything else — a typo would otherwise render as `todo`,
so finished work would quietly read as outstanding. When every task is done but the item still
sits before `verified`, that **drifts**: either it is finished, or the checklist is behind.

Keep the list flat. Individual steps belong in the plan document; the page carries the shape of
the work and where it has got to.

When the checklist is one somebody has to **execute** rather than read, declare `task_columns`
on the item as a list of `{key, label}` and give each task those keys: the page then renders
one row per step, in a container that scrolls sideways so the page body never does. The gate
fails on a column with no key or label, a duplicate key, or a key colliding with `name`,
`state` or `note`, and drifts when a step still to run leaves a declared column empty. Without
`task_columns` the checklist is byte for byte the list it has always been.

A task may also carry `result`, which is how it turned out rather than where it sits in the
run: a step can be `done` and have failed. Where any step carries one, the table gains a
leading `Result` column; `pass`, `fail`, `covered` and `blocked` each get a word and a mark so
they are separable without colour. And `note` may be a list of strings, rendered as bullets in
the table's continuation row and in the plain checklist alike. The gate fails on a result that
is not a word, and on a note that is neither prose nor a list of points.

## Catching the page going stale

Structure was never what rotted. What rotted was a page that quietly stopped being true while
every structural check stayed green: an item reading "waiting for its first real message"
while its own task list recorded the work as done.

The gate now checks two more things:

**Contradiction — fails.** Not-yet language in an item whose own tasks are done. A capability
marked `not-started` while an active item works on it. These are the page disagreeing with
*itself*, so a script can be certain without knowing anything about the world.

**Readability — fails on the unambiguous, drifts on the rest.** A stranger should be able to
read the page. Insider shorthand fails; undefined jargon, bare cross-references like "P2",
and sentences over 55 words drift.

Both are FAIL rather than DRIFT on purpose: the end-of-turn hook blocks on FAIL, so a turn
cannot end on a self-contradicting page. It stops depending on anyone remembering to look.

## Saying what waits on what

When one item cannot start until another finishes, record it as data:

```json
{ "name": "Screening", "blocked_by": ["Containment"], … }
```

A dependency described in a plan document, or explained in conversation, exists nowhere a check
can see it — which is how an item stays marked active for days while the work it waits on sits
unstarted at the bottom of the queue.

- **Fails** when an active item with outstanding work waits on something only queued. One of the
  two is in the wrong place.
- **Fails** when it waits on something not on the plan at all.
- **Drifts** when it still waits on something already finished.
- **Drifts** when every unfinished task on an active item is blocked — that item is waiting, not
  active.

## The conventions the page depends on

Three of them, each now checked, because each is what lets a reader answer a question in one
glance rather than by comparing candidates.

**One item under Active at a time**, with its checklist. A second one **fails** unless the
plan declares `meta.allow_multiple_active: true`.

**A finished item is moved to `done` and gains a `period` and an `outcome`.** Moved, not
rewritten: the page reads a carried-over `status` in the outcome slot and `plan_file` in the
`file` slot, so nothing is lost on the way across. A finished plan missing either **drifts**.

**Long sections get rolled, not truncated.** Run `scripts/roll.py` when the gate reports that
records have aged off the front page. It moves them, in full, into `plan/archive/done.json`,
`archive/changelog.json` and `archive/backlog.json`, and the Done and Next headings then read
"N older in archive/done.json" from the file itself. Before 0.14.0 this was done by hand into
a markdown file with the count typed into the heading hint; that count went stale within days,
which is why it is derived now. Headings remain data (`meta.headings`) for the title and the
hint text; the archive count is appended by the renderer.

## The gate

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py"
```

Two kinds of finding, kept separate on purpose:

- **FAIL** — structural. A capability claiming progress with no evidence. An item past
  *planned* with no plan document. A second item under Active. An invariant in an unknown
  state. A parked question with no trigger. The page out of sync with the JSON. Exit code 1.
- **DRIFT** — heuristic. Uncommitted work outside the plan directory while the plan sits
  untouched. The last substantive commit newer than the plan's timestamp. A plan nobody has
  touched in a fortnight. A finished plan with no period or no outcome. A legacy
  `meta.version` disagreeing with `plan_version`. Exit 0 unless `--strict`.

**It deliberately does not check whether the plan is true.** No script can. It makes
*forgetting* visible; judging accuracy stays a human and agent job.

## Edge cases

Hazards found while designing, kept until they are dealt with:

```json
"edge_cases": [
  { "id": "E3", "case": "Redaction fails open when the model returns bad JSON.",
    "surface": "privacy layer", "status": "open",
    "mitigation": "Fail closed: refuse the turn rather than forward raw content." }
]
```

`status` is `open`, `mitigated` or `accepted`. The gate fails on an `accepted` case with no
reasoning, because accepting a hazard silently is how it stops being a decision.

## Checking the plan against reality

The gate above checks that the plan is *consistent*. It cannot tell whether it is
*true* — unless the plan says how to find out:

```json
"assertions_setup": "ssh host 'echo pid=$(systemctl show app -p MainPID --value)'",
"assertions": [
  { "claim": "the service never restarted",
    "run": "grep '^pid=' \"$PLAN_FACTS\" | cut -d= -f2",
    "expect": "3001002" }
]
```

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" --verify
```

**These never run automatically.** They are shell commands read from a file in the
repository; running them on session start would mean cloning a repository executes
its author's commands. Explicit `--verify` only, never from a hook, and there is a
test that proves it.

**Use `assertions_setup`.** One command gathers everything into `$PLAN_FACTS`, and
each assertion reads from that. Assertions that each open their own connection are
slow, and eight of them in a row is enough to trip a host's SSH rate limiting and
lock you out of your own machine. Keep the remote side trivial and do the matching
locally — nested quoting is the most common cause of a check that errors, and an
errored check looks exactly like a false claim.

## The hooks

| Event | What happens |
|---|---|
| `SessionStart` | Current state — active item and stage, next up, failing invariants, gate results — is injected before the agent's first word |
| `PreCompact` | Fires when context is about to be summarised away, which is when working state gets lost. Flush to the plan first |
| `Stop` | Runs the gate at the end of every turn and **blocks on FAIL**, so a structurally broken plan cannot survive to the next session. Drift never blocks — it fires during ordinary work, and a hook that interrupts every turn gets disabled. Guarded three ways against looping: honours `stop_hook_active`, never raises the same failures twice per session, fails open on error |

Both are **silent in projects with no plan file**, and both **fail open** — a broken
briefing never blocks a session.

## Your own diagrams

The engine ships none: diagrams are about one project's specific mechanism and do not
generalise. To add your own, create `plan/figures.py`:

```python
CSS = """
  .my-box{fill:none;stroke:var(--line)}
  .my-lbl{font-size:12.5px;fill:var(--ink)}
"""

def build(data):                  # data is the parsed plan.json
    return "<figure>…</figure>"   # any HTML; inline SVG works well
```

**Ship the CSS with the markup.** An SVG `<rect>` with no fill rule renders **solid black
with invisible text**, so a figure whose styles are missing looks like a broken page rather
than a plain one. The module-level `CSS` string is appended to the page stylesheet, so your
rules can use the same theme tokens (`--ink`, `--line`, `--accent`, `--done`, `--gap`) and
work in light and dark automatically.

The renderer picks the module up automatically, and skips the section if it is missing or
raises — a broken figure never costs you the page.

Then look at what you drew:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/figcheck.py"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/roll.py"       # when the gate says records have aged off the front page
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sync.py"       # after ANY change: refresh view facts, render, gate — the one command
```

It writes every figure to `plan/.figures/` as its own standalone page, screenshots each with
whatever headless browser is on the machine, and **exits 1** on a label that crosses the right
edge of the drawing or two labels printing over each other on one baseline. A label that may
spill its own box is printed as a note rather than a failure, since a label deliberately placed
beside a box trips the same estimate. Font sizes are read from the page's own stylesheet, so
restyling a figure cannot leave the checker measuring a drawing nobody has. No browser found is
not a failure: the geometry checks still run.

Whether the figure tells the truth about the system is the part no script can do. Open the
screenshots. Reasoning about coordinates is not looking, and both of the faults above have
shipped in a figure that had already been read carefully.

## Facts quoted in more than one place

Numbers that appear in both the prose and a figure belong in `facts`, once:

```json
"facts": { "skills": "61", "subagents": "5" }
```

Figures receive the whole plan, so they read `data["facts"]` rather than restating the
number, and they take any status they show from the capability, invariant or item it belongs
to rather than hardcoding it. A figure that hardcodes a fact will eventually disagree with the table above it —
this removes the possibility rather than checking for it afterwards.

## Configuration

Optional `.plan-layer.json` in the project root, if the defaults do not suit:

```json
{ "plan_dir": "plan", "plan_file": "plan.json", "page_file": "index.html" }
```

## Schema

[`schema/plan.schema.json`](schema/plan.schema.json) documents every field. **Every section
is optional** — a project that fills in only `plans` gets a page with only plans on it, and
nothing looks broken.

## Known gaps

Two things this deliberately does not do yet — no independent reviewer, and no way for a human
to dispute a claim in the file itself. History is now **kept** (0.14.0 rolls it into
`plan/archive/` in full) but not yet **readable** from the page; an archive index is queued.
Since 0.14.0 the plugin plans with itself: its own `plan/plan.json` sits at the root of the
marketplace repository. Each gap is written up with the evidence that revealed it and a sketch
of the fix in [ROADMAP.md](ROADMAP.md).

## Durability

The plan and the page are written atomically — to a temp file, then renamed. An interrupted
write leaves the previous version intact rather than a truncated one, and a concurrent reader
never sees a half-written file. This is not theoretical: the naive version was reproduced
destroying `plan.json` with a single Ctrl-C.

## Licence

MIT.
