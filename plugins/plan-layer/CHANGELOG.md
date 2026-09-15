# Changelog

## 0.12.0 — 2026-09-14

**A checklist someone has to execute is a table, not prose.**

The first consumer was about to run a manual acceptance pass of ninety four
steps, each with five fields: what it tests, which seat it is sent from, what to
send, what counts as a pass, and how to do it. Rendered as a name with a
paragraph under it, that cannot be scanned, and the person running the pass
works from the plan document instead and stops updating the page.

- **An item may declare `task_columns`**, a list of `{key, label}`. Each task
  then carries those keys alongside `name`, `state` and `note`, and the
  checklist renders as one row per step: the step with its mark and name first,
  then the declared columns in order. A task missing a key gets an empty cell.
- **`note` keeps its job.** It renders as a full-width line under its own row,
  which is where the evidence that a step passed belongs.
- **Nothing changes without columns.** The list markup is byte for byte what it
  was, and a test asserts the exact string rather than trusting it.
- **The table sits in the page's existing scrolling container**, so it scrolls
  sideways inside its own box on a phone and the page body never does.
- **The gate fails** on a declaration that cannot produce a readable table: not
  a list, a column with no key or no label, a duplicate key, or a key colliding
  with `name`, `state` or `note`, where the value would land on the step's own
  name, state or note. **It drifts** when a step still to run leaves a declared
  column empty, naming the step and the column, because that step cannot be run
  from the page. A done step is exempt: once it has passed, its instructions are
  history.

## 0.11.0 — 2026-09-13

**The plugin catches up with the plan it renders.**

The first real consumer had grown a shape the plugin never described, so a
second project starting from `init` would have had to rediscover all of it.

- **The schema documents every field that plan actually uses**: the top-level
  `facts` block, `capabilities[].short`, the whole finished-plan shape
  (`period`, `outcome`, `file`, `notable`, and `tasks` as a summary string once
  condensed), arbitrary `for_` keys in the contract, the `assertions_verified`
  stamp the gate reads, `assertions[].match` and `timeout`, and the legacy
  `meta.version` duplicate. Two fields written on a queued item that render
  nowhere are now named as such, so nobody assumes they appear.
- **The template ships the sections a plan grows into**: north star and owner,
  an empty `facts`, `systems`, `edge_cases` and `assertions`, and a `headings`
  map. All empty or one placeholder line, and the gate stays green on it.
- **The conventions are written down** in the skill and the README: one active
  item at a time with its checklist, a finished item moved to `done` with a
  period and an outcome, older entries archived to a sibling markdown file with
  a pointer in the heading hint, headings as data, figures deriving everything
  from the plan.
- **The gate holds three of them.** A second item in `plans.now` **fails**
  unless `meta.allow_multiple_active` says the project runs several streams on
  purpose. A finished plan with no `period`, or with nothing recorded about
  what it produced, **drifts**; a carried-over `status` counts as the outcome,
  because the page already renders it in that slot. A `meta.version` that
  disagrees with `plan_version` **drifts**, since one of the two is wrong and
  only one is read.
- **The figure check ships with the plugin.** `scripts/figcheck.py` extracts
  every figure into its own page, screenshots it with whatever headless browser
  is on the machine, and fails on a label crossing the right edge or two labels
  printing over each other on one baseline. Font sizes are read from the page's
  own stylesheet rather than carried in the checker, which is what makes it
  generic. It had been living in the consumer's own repository for a week.
- **The gate lists in both documents** were several releases behind what
  `check.py` reports.

Nothing in the renderer changed: the consumer's page re-renders byte for byte
identical through 0.11.0.

## 0.10.0 — 2026-09-03

**One vocabulary, declared once — and a raw Python repr taken off the page.**

The page was painting nine separate status vocabularies and explaining none of
them, so a reader had to reverse-engineer all nine. That absence is also how
they drifted into each other, one section at a time.

- **The page now prints a key**, generated from the same tables the sections
  render from. A marker cannot appear on the page without appearing in the key,
  and cannot mean one thing in a table and another in a card. Only the families
  a plan actually uses appear, so a project with no edge cases gets no
  edge-case row. A test asserts the coverage and was proven able to fail by
  planting a state the key does not list.
- **Three invariant states now render three ways.** `holding`, `at risk` and
  `broken` had two renderings between them: anything that was not holding was
  painted the same red. "At risk" and "broken" call for different responses.
- **`Planned` is no longer the same green as `Done`.** It takes the accent
  colour, which is already the colour of the `planned` stage chip — so
  "planned" is one colour everywhere on the page.
- **"Next" cards are no longer red.** Red is a gap or a hazard. Eleven
  red-edged cards under a heading called "Next" read as eleven problems; they
  are now the neutral in-between colour.
- **One label per state.** The capabilities table said "No plan" and the plan
  cards said "No plan written yet" for the same thing.
- **Edge-case and invariant states are pills**, like every other status on the
  page, and Title-case like every other label. An edge case's *surface* stopped
  borrowing `.trigger`, which means "when this must be answered" in the parked
  list — the same rendering in the same slot for two unrelated things.

**A pulsing dot marks work in flight** — the active plan card, an active step,
the `building` stage chip and the `In progress` build pill, and nowhere else. A
soft radial ring over 2.2s, one accent colour, no bounce. It is never the only
cue: a text label always sits beside it, and where it replaces a glyph the state
is also spoken, so the four step states are all reachable without seeing colour.
`prefers-reduced-motion` keeps the dot and its colour and drops only the ring.

**`sec_done` printed a Python repr on the page.** Items are MOVED from `now` to
`done` rather than rewritten — which is what the skill tells the agent to do —
so a finished item routinely still carries the active shape. `str()` on a list
of task dicts put roughly 1,100 characters of `[{'name': ..., 'state': ...}]`
onto a real page, while the same shape mismatch silently dropped the item's link
(`plan_file`, not `file`) and its entire explanation (`status`, not `outcome`).
All three shapes are now read. The original shape renders exactly as before.

Also: a checklist row wraps with a floor on both columns. Without one, a note
carrying real evidence took the width it wanted and squeezed the task name into
a three-line column.

No new palette tokens, so the WCAG AA contrast tests still cover everything the
page paints. No plan-file schema change: a plan with no `tasks`, `edge_cases`,
`invariants` or `figures` renders as it did before.

## 0.9.2 — 2026-08-17

**Packaging caught up with the code.** Six releases shipped in a week and the
things a stranger reads had fallen behind the things they describe.

- **Eight release dates in this file were the literal text `%s`** — a format
  string that was never substituted, going back to 0.3.0. Recovered from the
  commits that bumped each version rather than guessed.
- **The schema was missing five fields it should define:** `capability`,
  `blocked_by`, `edge_cases`, `assertions` and `assertions_setup`. The schema is
  the contract for anyone adopting this; an incomplete one is worse than none,
  because it looks authoritative.
- **The marketplace listing had no `whenToUse`.** Someone browsing could see what
  the plugin *is* and not when to reach for it.
- **The README did not mention `blocked_by`**, shipped hours earlier.
- **The ROADMAP was updated honestly rather than tidily:** gap 2 is partly closed
  (the gate now catches the page contradicting itself), gap 3 is unchanged and is
  now the most valuable — every miss so far was caught by a human reading the
  page, and there is still no way for them to mark a claim disputed.

No behaviour change.

## 0.9.1 — 2026-08-17

**Drift is now shown to the human the moment it appears.** It was collected at
the end of every turn and thrown away, surfacing only at the next session start
— so the same staleness went unnoticed for days at a time.

The end-of-turn hook now reports it through `systemMessage`: visible, and still
non-blocking.

One distinction keeps it from becoming noise. **Work-in-progress** signals
(uncommitted files, a commit newer than the plan) fire constantly and correctly
while someone is mid-task; they stay at session start, where they read as "here
is where you left off". **Staleness** signals — the page no longer matching
reality — surface immediately.

A notice that is always present is one nobody reads.

## 0.9.0 — 2026-08-17

**Dependencies between items are now data.** An item may declare
`blocked_by: ["another item's name"]`.

Prompted by a real miss. An item sat marked *active* for three days while the
work it depended on sat unstarted at the bottom of the queue. The dependency
was written in a plan document and stated in conversation, and therefore
existed nowhere a check could see it. The human caught it; the gate could not.

- **Fails** when an active item with outstanding work waits on something that is
  only queued — one of the two is in the wrong place.
- **Fails** when an item waits on something not on the plan at all.
- **Drifts** when an item still waits on something already finished.
- **Drifts** when every unfinished task on an active item is blocked, because
  that item is waiting rather than active.

Proven by replaying the exact state that went unnoticed: with the dependency
recorded, it fails immediately.

## 0.8.1 — 2026-08-14

**Figures must not ask for facts that do not exist.** A drawing that reads a
number from the plan degrades silently into "?" if that number is renamed or
removed, and nobody re-reads a picture they have already seen. Drifts now.

Prompted by the same failure one layer down: three figures still showed a
component as unbuilt four days after it was built and used, because figures
hardcode status. The durable fix is that a figure reads its state from the
plan; this check makes sure the reading still resolves.

## 0.8.0 — 2026-08-14

**The gate now catches the page contradicting itself, and catches it going
opaque.** Structure was never what rotted. What rotted was a page that quietly
stopped being true while every structural check stayed green — an item reading
"waiting for its first real message" while its own task list recorded the work
as done, and a capability saying a channel did not work while the active plan
said it did. Four days, unnoticed, until a human read it.

The published pattern for living documentation is three parts: detect
staleness, route it to a person, make the fix cheap. Routing and cheap fixes
already existed. Detection did not.

- **Contradiction checks — FAIL.** Not-yet language in an item whose own tasks
  are done. A capability marked `not-started` while an active item works on it,
  or while finished work is filed against it. These are internal disagreements,
  not judgements about the world, so a script can be certain.
- **Readability checks.** The property the page exists for: a stranger should
  be able to read it. Insider shorthand **fails**; jargon absent from the
  glossary, bare cross-references like "P2", and sentences over 55 words
  **drift**.
- FAIL rather than DRIFT is the whole mechanism — the end-of-turn hook blocks
  on FAIL, so a turn cannot end on a self-contradicting page. It stops
  depending on anyone remembering to look.
- Six tests, including the exact failure that prompted this, and one asserting
  the shipped template does not trip its own new checks.

## 0.7.0 — 2026-08-10

**An active plan can now show its tasks.** Before this, an active item could
name a plan document and say nothing about what was in it, so the page told a
reader "a plan exists, here is a filename you cannot open" — the one thing this
page is meant to prevent. Found the way these things are always found: the human
asked why he could not see the active plan, and the honest answer was that it
was never rendered.

- `plans.now[].tasks` and `plans.next[].tasks` — a flat checklist of
  `{name, state, note?}`, `state` in `done | active | todo | blocked`.
  Deliberately flat: individual steps belong in the plan document, while the
  page carries the shape of the work and where it has got to.
- The gate **fails** on an unrecognised state. A typo would otherwise render as
  `todo`, so finished work would silently read as outstanding.
- The gate **drifts** when every task is done but the item still sits before
  `verified` — either it is finished, or the checklist is behind.
- Five tests, including one asserting a plan with no `tasks` key renders exactly
  as it did before.

## 0.6.1 — 2026-08-10

- Orientation now comes before the contract. A first-time reader was being handed
  "read this first, every session" before being told what the project is.


## 0.6.0 — 2026-08-10

Readability, measured rather than guessed. A page nobody can be onboarded from is not a
shared surface, it is an archive.

- **"Active now" moved to the top**, above the figures. It was at position nine, behind five
  diagrams and three tables — the single most-read fact on the page, buried.
- **The changelog shows the five most recent entries**, with a line saying how many are left
  off. Twenty entries was 15%% of the page, and git holds the full record anyway.


## 0.5.0 — 2026-08-10

- **Edge-case register.** A section for hazards found along the way, each with a surface and a
  status of `open`, `mitigated` or `accepted`. They surface during design conversations and
  otherwise die in a chat log.
- The gate requires a valid status, and **fails on an `accepted` case with no reasoning** —
  accepting a hazard silently is how it stops being a decision.


## 0.4.0 — 2026-08-10

The loop said "finish every turn by running the gate". That was an instruction, and the
human ended up being the one who noticed when it was skipped.

- **Stop hook.** The gate runs at the end of every turn and **blocks on FAIL**, feeding the
  failures back so they get fixed before the turn ends. Structural dishonesty can no longer
  survive to the next session.
- **Drift never blocks.** Every drift signal fires during ordinary work; a hook that
  interrupts every turn is a hook someone disables. Drift is reported at session start.
- **Three loop guards**, because a Stop hook that blocks forever makes a session unusable:
  it honours `stop_hook_active`, never raises the same failures twice in one session
  (keyed by session + project + failure set), and fails open on any internal error.
- **New drift signal:** an invariant that is not holding while its detail overlaps work
  already in `plans.done` — a stale alarm teaches people to ignore alarms. Found by hand
  on a real plan before it was automated.
- **`facts`**: a place for numbers quoted by both the prose and the figures, so the same
  value cannot be typed twice and drift. A figure once said "6 sub-agents" while every
  other statement said 5.


## 0.3.2 — 2026-08-10

- **Atomic writes.** `open(path, "w")` truncates immediately, so an interruption between
  the truncate and the last byte left a half-written file. Reproduced: a Ctrl-C mid-write
  left `plan.json` unparseable — data loss in the one file this tool exists to protect.
  Both the plan and the page are now written to a sibling temp file and renamed, so a
  reader sees the old contents or the new ones and never a mixture. fsync before the
  rename, so a power loss cannot make the rename durable while the contents are not.
- Three tests, including one that interrupts a write and asserts the original survived.


## 0.3.1 — 2026-08-10

- The commit-vs-plan drift signal now tolerates 120 seconds. Plan and commit are normally
  written moments apart, and reporting "00:44Z is newer than 00:44Z" is true to the second
  and reads as nonsense. A check people learn to dismiss is worse than no check.

## 0.3.0 — 2026-08-09

The gate could check that a plan was internally consistent. It could not check
whether the plan was TRUE. Now it can, if the plan says how.

- **Executable assertions.** A plan may declare `assertions` — a claim, a command,
  an expected result — and `check.py --verify` runs them against the real system.
- **Never automatic.** Assertions are shell commands read from a repository file.
  Running them on session start would mean cloning a repo executes its author's
  commands, so they run only on explicit `--verify`, never from a hook. There is a
  test that opening a project cannot trigger one.
- **`assertions_setup`: one gather, many checks.** Eight assertions that each opened
  their own SSH connection tripped a host's `ufw limit 22/tcp` rule and locked us out
  of our own server. The claims were all true; the method was the problem. A single
  setup command now caches facts to `$PLAN_FACTS` and assertions read that.
- **An errored check is reported as errored, not as a failed claim.** They look
  identical from the outside and mean opposite things.
- **Seven more structural checks:** duplicate capability ids, two items claiming one
  plan document, an invariant alarming with no detail, a parked question with no
  trigger, a future or unparseable timestamp, an item finished but still active,
  assertions declared and never run.


## 0.2.0 — 2026-08-10

- **Plan items can name the capability they serve** (`capability: <id>`), shown as a chip
  beside the item. Without it a plan list and a capabilities table are two documents that
  happen to share a page — a reader cannot tell that "tenant identity in traces" IS the
  observability row.
- The gate enforces it: a dangling reference **fails**; an unlinked item **drifts**.
- New drift signal: a capability whose evidence reads as blocked while nothing is queued
  against it — a claim the plan never follows up on.
- Capabilities may carry a `short` label for figures, since a name that reads well in a
  table row overflows a diagram box.

## 0.1.4 — 2026-08-10

- **Docs: the update instruction was wrong.** It said `claude plugin marketplace update`
  was enough. It is not — that refreshes the catalogue and leaves the installed plugin
  where it was. Both commands are needed, and the version must be bumped in both
  manifests first. Found by following the instruction and watching nothing change.
- Accessibility stated where it is relevant: the page meets WCAG AA in both themes, and
  that is a test, not a claim.

## 0.1.3 — 2026-08-09

- **Light palette now clears WCAG AA.** `--muted` measured 4.31:1 and `--active` 4.09:1
  against the card ground, both just under the 4.5:1 body-text threshold and both used
  for real content (section hints, glossary definitions, diagram sub-labels). Darkened to
  4.89:1 and 4.94:1. The dark palette already measured 5.2:1 and up; unchanged.
- Two tests assert every text token against both grounds, in both themes. Colour is the
  one thing that cannot be eyeballed.

## 0.1.2 — 2026-08-09

- **Figures can ship their own CSS.** A `figures.py` may define a module-level `CSS`
  string, appended to the page stylesheet. Markup alone was never enough: an SVG `rect`
  with no fill rule renders solid black with invisible text, so a figure without styles
  looks like a broken page rather than a plain one. Found by shipping exactly that.
- The renderer now says so out loud when a figures module supplies markup and no CSS.

## 0.1.1 — 2026-08-09

- Drift message renders both timestamps in UTC. git reports commit times with a local
  offset while `meta.updated` is written as Z, so a correct finding printed as
  `17:26` being "newer than" `21:22` — true, but unbelievable. A check nobody
  believes is a check nobody acts on. Regression test added.

## 0.1.0 — 2026-08-09

First release. Extracted from a working setup rather than designed in the abstract:
every piece here was earning its keep in a real project before it became a plugin.

- `plan.json` as shared state; self-contained HTML page as the view
- Six-stage development cycle, each stage naming what it looks like when skipped
- `check.py` gate separating structural FAIL from heuristic DRIFT
- `SessionStart` and `PreCompact` hooks — silent where uninvited, fail open
- Project-supplied diagrams via an optional `plan/figures.py`
- Every section optional; headings overridable per project
- Zero third-party dependencies, asserted by a test
