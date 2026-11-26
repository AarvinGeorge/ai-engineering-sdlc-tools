# plan-layer

A shared planning surface between a human developer and a coding agent.

**One JSON file is the state.** **A self-contained HTML page is the view.** **A gate catches
drift.** **Session hooks brief the agent before the first word is typed.**

## Use cases

- **You come back after a week and ask the agent where things stand.** A session hook has already
  given it the active item, its stage and the queue, read from `plan/plan.json`. Ask for
  `/plan-layer status` and you get the same three things, not a guess from memory.
- **The plan says one thing and the work says another.** The gate reads the plan against itself.
  Mark a dependency finished and forget the item that waited on it, and `/plan-layer check` prints:

  ```
  DRIFT  item 'Login page' still says it waits on 'Mail provider', which is finished
  ```

  A contradiction (two active items, a missing plan file for work being built) is a `FAIL` instead.
- **You want to read the plan without a terminal.** `/plan-layer sync` re-renders `plan/index.html`,
  a single page with no scripts or network calls. Open it locally or publish it. If the JSON changes
  and the page does not, the page says it is stale.
- **You stop for the day, or hand the work to someone else.** `/plan-layer pause` writes
  `plan/HANDOFF.md` and marks the plan paused. The next session's brief tells the agent to read the
  handoff before anything else. `/plan-layer pause --resume` clears it.
- **Someone moves a stage by hand while the tracker is mirrored.** With `meta.controller.one_writer`
  on, only `move.py` may change a stage, so the hand edit turns the gate red. `/plan-layer check` prints:

  ```
  FAIL   stage of E-01.S2 is 'verified' but move.py last wrote 'building' — changed by hand; revert the hand edit, or run move.py --adopt (with the owner's say-so)
  ```

  Revert the edit and make the move with the one writer, `move.py E-01.S2 --stage verified`:

  ```
  move: E-01.S2 building -> verified
  NEXT: run sync.py --tracker and reconcile the tracker
  ```

  Until the tracker is reconciled the gate stays red with
  `tracker mirror (generic): the rows the plan now expects differ from those last reconciled`.
- **A backup job lists five agents of ten.** Declare the agents once under `inventory` and name the
  backup script as a list that must cover them. `/plan-layer check` prints:

  ```
  FAIL   inventory 'agents': list 'nightly backup' covers 5 of 10 — missing agent-06, agent-07, agent-08, agent-09, agent-10
  ```

  Add the five to the script, or exempt each one with a written `why`.
- **An invariant says "holding" and nobody has looked.** Give it a `check`, a command whose exit code
  is the truth. Declare it in `plan.json`:

  ```json
  { "rule": "no debug prints left in src", "state": "holding", "check": "! grep -rn 'print(\"DEBUG' src" }
  ```

  `check.py --verify` runs it and prints:

  ```
  FAIL    invariant 'no debug prints left in src' (state 'holding'): check exited 1: src/app.py:1:print("DEBUG x")
  ```

  The hand-set state is not changed and the verified stamp does not move until the check passes.
- **A one-week take-home or a spike.** `/plan-layer init --light` gives you the state file, the page
  and the gate, without figures, archive or rolling.

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

Then, in any project you want it for, ask the agent to run `/plan-layer init` — or
`/plan-layer init --light` for a short project (see "Light and full" below). In Claude Code this
runs through the plan-layer skill, which follows the steps in `skills/plan-layer/SKILL.md` ("init").
There is no `init` script, so outside Claude Code, or if you prefer to do it by hand, the
equivalent is:

```bash
mkdir -p plan
cp <plugin>/templates/plan.json plan/plan.json      # or templates/plan.light.json for --light
cp <plugin>/templates/MAP.md plan/MAP.md            # skip for --light
# edit plan/plan.json: meta.project, meta.subtitle, meta.updated (from a clock: date -u +%Y-%m-%dT%H:%M:%SZ),
# and replace the placeholder capability and next item with real ones
python3 <plugin>/scripts/render.py && python3 <plugin>/scripts/check.py
```

`<plugin>` is the installed plugin folder (or your clone's `plugins/plan-layer`). Commit
`plan/index.html`: it is generated on purpose so anyone can open the page without running anything.

**The fresh template fails the gate until `meta.updated` is set from a clock.** It ships with a
placeholder (`REPLACE WITH ISO-8601 UTC READ FROM A CLOCK`) on purpose: a date recalled from memory
is the usual way a plan goes stale, so the gate refuses the template until a real time is written.
That first red `check.py` is expected, not a broken install. A DRIFT line about the next item naming
no capability is a signal, not a failure.

**Nothing to install beyond Python 3.10 or newer** (check `python3 --version`; the system Python on
macOS can be older). Zero third-party packages, by design.

## What you get

```
your-project/
  plan/
    plan.json      the state — you and the agent both edit this
    index.html     the view — generated, committed, never hand-edited
    figures.py     optional: your own diagrams
    MAP.md         the map a fresh session reads first: what lives where, the commands, the reading rules
    archive/       history in full, machine-readable: older done items, old changelog, the queue beyond
                   the front page; written by sync.py, committed with plan.json and index.html
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
  running it twice is safe. Since 0.16.0 `sync.py` rolls automatically and prints what moved
  (`--no-roll` opts out). The gate says when it is due, and the Done and Next headings gain
  "N older in archive/…" counted from the archive file, never typed. Keep-counts are
  overridable per project under `roll` in `.plan-layer.json`.
- **Views** (0.15.0) are drawings that live beside the page rather than on it — the first kind is
  Archify, whose exported SVG carries its own 132 KB stylesheet and font. `plan.json` `views[]`
  lists each one: the spec in the repository (the truth), the published URL (the pointer), and two
  facts written only by `scripts/sync.py`, never typed: the spec's SHA-256 and the commit it was
  measured at (`meta.repository.revision`). The gate says when a drawing has gone stale: the spec
  changed since delivery, the live revision moved past it, or the spec is missing. A deploy's last
  step is `sync.py --live-revision <sha read off the running system>`. `init` can copy a starter
  spec (`templates/topology.architecture.json`); the tested companion is Archify, installed from its
  author, never bundled.
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

**Long sections get rolled, not truncated.** `scripts/sync.py` rolls them automatically (0.16.0;
`scripts/roll.py` does the same by hand, `--dry-run` to preview). It moves them, in full, into `plan/archive/done.json`,
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

An invariant can prove itself the same way. Give it a `check`: a command whose exit code is the
truth (0 holds). `--verify` runs it after the assertions, with the same `$PLAN_FACTS`; a non-zero
exit is a FAIL naming the invariant, `--verify` exits 1, and the verified stamp does not move.
The invariant's `state` stays yours to set; the run tells you when it is wrong.

```json
"invariants": [
  { "rule": "the unit suite is green", "state": "holding",
    "check": "python3 -m unittest discover -s tests 2>&1 | tail -1 | grep -Eq '^OK( \\(skipped=[0-9]+\\))?$'" }
]
```

The same rule applies: never run automatically, never from a hook, `sync.py` or the gate. A check
runs as `bash -lc` with your full environment and write access, the same trust as the project's own
scripts, which is why it runs only on `--verify`. It gets no stdin, a 60-second timeout, and its
whole process group is killed on timeout.

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
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sync.py"       # after ANY change: roll, refresh view facts, render, gate — the one command
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

## Light and full

(0.16.0) A one-week project needs the state file and the gate, not figures or an
archive. `meta.mode: "light"` (written by `init --light` from `templates/plan.light.json`) keeps every structural FAIL and drops the full-only ceremony: figures, the archive and rolling.
Archify views are opt-in in both modes: declared views are checked exactly as in full mode
(missing spec, stale spec sha, live revision); no views declared means nothing is enforced.
Absent means full, so every existing plan is unchanged. Change the one field to move between them.

Works with **`engineering-method`** (optional), the sibling plugin that carries the engineering
method; plan-layer stays a state tool.

## Controller: one writer, tracker, rules, inventory, handoff

All of this is opt-in; a plan without `meta.controller`, `meta.tracker` or `inventory` behaves
exactly as in 0.18.0. The pattern is a reconcile loop: the plan is the declared state; git, the
tracker and the files you name are observed; `scripts/controller.py` computes the one diff, and
the gate, the handoff and the hooks all read it. Drift is a red gate, and a script or a hook
fires the check, never the agent's memory.

**One writer.** Set `meta.controller: {"one_writer": true}` (with `meta.naming: "work-ids"`) and
run `scripts/move.py --adopt` once to stamp the current state. From then on `move.py` is the only
writer of stage, task state, bucket and release stage (`--stage`, `--task <name> --state <s>`,
`--to now|next|done`). The stamp lives in `plan/controller-state.json`; a field that differs from
it is a hand edit and FAILs the gate, and `move.py` refuses to write until it is reverted or
adopted. `--adopt` is for the owner's deliberate edits only. The skill lists every field and its
one writer as a table checked against the code.

**Tracker mirror.** Set `meta.tracker` (`{"kind": "notion", "target": "<database>"}`) and
`scripts/tracker.py` derives the rows an external tracker should hold from the plan, diffs them
against rows the agent fetched through that tracker's connector, and prints each fix as an
instruction. `sync.py --tracker [--actual <file>]` runs it with the normal sync. With
`meta.controller` set, an unreconciled tracker FAILs the gate; without it, it is DRIFT as before.
`meta.tracker.relational: true` mirrors epics, stories, tasks and releases as linked rows.
Adapters are data files in `trackers/` (Notion and a generic one ship; see `trackers/README.md`).

**Rules on events.** `meta.controller.rules` holds co-change rules: when a file matching
`if_changed` changed on the branch, a file matching each `then_changed` pattern must have changed
too. Each rule names the events it runs on: `stop`, `session-start`, `sync`, `pause` (the hooks
and scripts of those names) or a move, `stage:<id>` and `release:<stage>`. A failing rule refuses
the move. Worked example, an approval recorded before live work:

```json
{"name": "approval before production", "on": ["release:production"],
 "if_changed": ["deploy/*"], "then_changed": ["docs/approvals/*.md"],
 "why": "live changes need a recorded approval"}
```

On a branch that changed `deploy/compose.yml` and no approval, `move.py R-01 --stage production`
prints:

```
  move: refused -- the release:production rules fail; nothing written:
    - rule 'approval before production' on release:production: deploy/compose.yml changed but nothing matching docs/approvals/*.md did (live changes need a recorded approval)
```

Add `docs/approvals/r-01.md` and the same command prints `move: R-01 bench -> production`. The
rule proves that an approval file changed on the branch, not who wrote it or what it says; that
stays a human check. On the base branch there is no branch to measure: a session event reports
DRIFT ("measured nothing"), a move FAILs. A rule matches paths; it cannot run a check.

**Inventory parity.** Declare a list once and name every list that must cover it. Worked example,
ten agents and a backup script:

```json
"inventory": {"agents": {
  "items": ["agent-01", "agent-02", "agent-03", "agent-04", "agent-05",
            "agent-06", "agent-07", "agent-08", "agent-09", "agent-10"],
  "covered_by": [{"list": "nightly backup", "file": "ops/backup.sh"}]}}
```

With five agents in `ops/backup.sh` the gate prints
`FAIL   inventory 'agents': list 'nightly backup' covers 5 of 10 — missing agent-06, agent-07, agent-08, agent-09, agent-10`.
A plain file is matched by whole word (`agent-1` is not covered by `agent-10`); `"json":
"jobs[].host"` reads values from a JSON file; `{"list": "board", "tracker": true}` checks the rows
of the last tracker reconcile; `"from": {"file", "json"}` reads the inventory itself from a file.
An exemption is `{"item", "list", "why"}`, and the `why` is required. Inventory needs no
`meta.controller`.

**Pause and handoff.** `scripts/pause.py` writes `plan/HANDOFF.md` (time, git state, gate
result, active work, resume order, open questions, traps; all read at that moment) and sets
`meta.paused`; the session brief then opens with a PAUSED line. With `meta.controller` the note
adds the controller's diff, git per active item, and the decision ids added to
`meta.controller.decision_log` since the last handoff. It never blocks on what it finds.
`pause.py --resume` clears it.

## Configuration

Optional `.plan-layer.json` in the project root, if the defaults do not suit:

```json
{ "plan_dir": "plan", "plan_file": "plan.json", "page_file": "index.html" }
```

In `plan.json`: `meta.size_budget_kb` sets the size above which the gate drifts (default 200 KB),
and `meta.mode` picks light or full.

## Schema

[`schema/plan.schema.json`](schema/plan.schema.json) documents every field. **Every section
is optional** — a project that fills in only `plans` gets a page with only plans on it, and
nothing looks broken.

## Known gaps

Two things this deliberately does not do yet — no independent reviewer, and no way for a human
to dispute a claim in the file itself. History is now **kept** (0.14.0 rolls it into
`plan/archive/` in full) but not yet **readable** from the page; an archive index is queued.
Each gap is written up with the evidence that revealed it and a sketch
of the fix in [ROADMAP.md](ROADMAP.md).

## Durability

The plan and the page are written atomically — to a temp file, then renamed. An interrupted
write leaves the previous version intact rather than a truncated one, and a concurrent reader
never sees a half-written file. This is not theoretical: the naive version was reproduced
destroying `plan.json` with a single Ctrl-C.

## Licence

MIT.
