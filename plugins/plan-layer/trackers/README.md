# Tracker adapters

An adapter is one JSON file here, named `<kind>.json`. A plan opts in with
`meta.tracker: {"kind": "<kind>", "target": "<database url or id>"}`. Nothing else
in the plugin changes when you add one.

plan-layer never calls a tracker's API. The agent does, through that tracker's
connector. plan-layer derives what the rows SHOULD be (`tracker.py expected`),
compares them with the rows the agent fetched (`tracker.py diff --actual <file>`)
and prints each difference as an instruction to carry out.

## The adapter file

```json
{
  "kind": "mytracker",
  "description": "one line on the tracker and what must exist in it",
  "fields":     {"name": "Title", "status": "State", "stage": "Stage", "updated": "Updated", "link": "Link"},
  "status_map": {"intent": "...", "grounded": "...", "planned": "...", "building": "...",
                 "verified": "...", "recorded": "...", "paused": "Paused", "done": "Done"},
  "fetch": "how the agent reads every row with this tracker's connector"
}
```

- **fields**: the tracker's own column or property names for the five things
  mirrored. Rows in the `--actual` file use these names.
- **status_map**: one tracker value per plan stage, plus `paused` (what an active
  item shows while `meta.paused` is set) and `done`. A project with custom stages
  adds a key per stage id; a stage with no key is written as its own id.
  Every value must already exist as an option in the tracker.
- **fetch**: the instruction the agent follows to produce the actual rows: which
  connector call lists every row (all pages), and that the output is a JSON list
  of objects keyed by the adapter's field names.

A plan can override any of this without a new file: `meta.tracker.fields`,
`meta.tracker.status_map` (merged over the adapter) and `meta.tracker.recent_done`
(how many of the latest finished items to mirror, default 5).

## What is compared

Rows are matched on the work id at the start of the name (`E-01.S2`); a row whose
name lacks the id but matches the item's title is matched too and reported as a
rename. Name, Status and Stage are compared; Updated and Link are written when a
row is created and never compared. Rows for finished work that has rolled into
`plan/archive/` are known and never reported as strays.
