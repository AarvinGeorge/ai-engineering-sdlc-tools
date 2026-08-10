# Changelog

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
