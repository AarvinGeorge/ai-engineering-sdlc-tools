# plan/ — the map (read this before touching anything here)

**One truth: `plan.json`.** The page `index.html` is generated from it and is never edited by hand.
Drawings, if the project has any, come from `figures.py`. Everything else here is archive or tooling.

| Path | What it is | Edit? |
|---|---|---|
| `plan.json` | the live plan: what is active, next, recently done, parked, invariants, facts, glossary | yes, one key at a time, with a small script; never load it whole into context |
| `index.html` | the rendered page | never; run the renderer |
| `figures.py` | one function per drawing, assembled in `build()` | yes; read ONE function by name, never the whole file |
| `archive/` | history in full: older done items, old changelog, the queue beyond the front page, retired figures | append-only; read only when the question is about the past |
| `MAP.md` | this file | when the layout changes |

## The commands, in order, after any change

```bash
P="${CLAUDE_PLUGIN_ROOT:-$(ls -d ~/.claude/plugins/cache/ai-engineering-sdlc-tools/plan-layer/*/ | sort -V | tail -1)}"
python3 "$P/scripts/render.py"     # plan.json (+ figures.py) -> index.html
python3 "$P/scripts/figcheck.py"   # only if a figure changed; then LOOK at plan/.figures/NN.png
python3 "$P/scripts/check.py"      # the gate: FAIL blocks the turn, DRIFT is advisory
python3 "$P/scripts/sync.py"       # after ANY change: roll aged records, refresh views, render, gate
# then republish the page
```

## Rules that keep it small and true

- Smallest edit that makes the page true. Move an item between `now` / `next` / `done`; never duplicate it.
- `meta.updated` comes from the clock, never from memory. Bump `meta.plan_version` and append one changelog line per substantive change.
- The front page shows this month. `sync.py` rolls automatically and keeps the last 8 done, the last 10 changelog entries and the first 8 queued (plus one per capability); the rest live in `archive/` in full. Nothing is deleted.
- A figure shows the system as measured, never an invented topology. If two figures tell the same story, retire the older one.
- Numbers quoted in prose and in a figure live once, in `facts`.
- Never hand `plan.json` or `figures.py` to a subagent. Hand the slice it needs.
- Token cost lives in reading, not editing. Edit with scripts; read by key or by function.
