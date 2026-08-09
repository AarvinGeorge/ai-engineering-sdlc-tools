# Changelog

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
