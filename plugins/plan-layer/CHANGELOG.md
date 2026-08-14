# Changelog

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

## 0.6.1 — %s

- Orientation now comes before the contract. A first-time reader was being handed
  "read this first, every session" before being told what the project is.


## 0.6.0 — %s

Readability, measured rather than guessed. A page nobody can be onboarded from is not a
shared surface, it is an archive.

- **"Active now" moved to the top**, above the figures. It was at position nine, behind five
  diagrams and three tables — the single most-read fact on the page, buried.
- **The changelog shows the five most recent entries**, with a line saying how many are left
  off. Twenty entries was 15%% of the page, and git holds the full record anyway.


## 0.5.0 — %s

- **Edge-case register.** A section for hazards found along the way, each with a surface and a
  status of `open`, `mitigated` or `accepted`. They surface during design conversations and
  otherwise die in a chat log.
- The gate requires a valid status, and **fails on an `accepted` case with no reasoning** —
  accepting a hazard silently is how it stops being a decision.


## 0.4.0 — %s

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


## 0.3.2 — %s

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

## 0.3.0 — %s

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
