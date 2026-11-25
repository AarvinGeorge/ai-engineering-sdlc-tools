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

Only `name` and `status` are required in `fields`. `stage`, `updated` and `link` are
optional: a field the adapter does not declare is neither written nor compared. Rows
in the `--actual` file must be a bare JSON list as the tracker holds them, every value a
plain string (flatten selects, dates and the like when fetching); the object that
`tracker.py expected` prints is refused.

**A project's own adapter** goes in `plan/trackers/<kind>.json`. It is checked before
the plugin's `trackers/`, so it can add a tracker or replace a shipped one, and a plugin
update never overwrites it.

Example, Linear (issues have a state but no stage column), saved as
`plan/trackers/linear.json`, with `meta.tracker: {"kind": "linear", "target": "<team>"}`:

```json
{
  "fields": {"name": "Title", "status": "State", "link": "URL"},
  "status_map": {"intent": "Backlog", "grounded": "Backlog", "planned": "Todo",
                 "building": "In Progress", "verified": "In Review", "recorded": "In Review",
                 "paused": "Paused", "done": "Done"},
  "fetch": "List every issue of the team through the Linear connector (all pages); save a JSON list of {Title, State, URL} with every value a plain string (the state by name)."
}
```

A plan can override any of this without a new file: `meta.tracker.fields`,
`meta.tracker.status_map` (merged over the adapter) and `meta.tracker.recent_done`
(how many of the latest finished items to mirror, default 5).

## What is compared

Rows are matched on the work id at the start of the name (`E-01.S2`); a row whose
name lacks the id but matches the item's title is matched too and reported as a
rename. The full name (a different title on a matching id is a rename), Status and, when declared, Stage are compared; Updated and Link are written when a
row is created and never compared. Rows for finished work that has rolled into
`plan/archive/` are known and never reported as strays; a row for finished work must say the `done` value.

## Relational mode (0.19.0)

The flat mirror above holds one row per plan item. Relational mode mirrors the work as
linked rows: epics, stories, tasks and releases. Turn it on with
`meta.tracker.relational: true`; it needs `meta.naming: "work-ids"` and an adapter that
declares `relations`. Without the flag the flat mirror is unchanged.

The adapter adds four keys (both shipped adapters have them):

```json
{
  "relations": {"epic": "Epic", "story": "Story", "release": "Release"},
  "task_status_map": {"todo": "Not started", "active": "In progress", "blocked": "Blocked", "done": "Done"},
  "release_status_map": {},
  "relational_fetch": "how the agent reads every row of every database, tagged by kind"
}
```

- **relations**: the tracker's names for the link columns: a story's epic and release, a
  task's story. All three are required in relational mode.
- **task_status_map**: one tracker value per task state. **release_status_map**: one per
  release stage; a stage with no key is written as its own name.
- **relational_fetch**: used in place of `fetch`. Each row in the `--actual` list carries
  `"kind": "epic" | "story" | "task" | "release"` (by the database it came from), and a link
  is flattened to the linked rows' titles joined by `", "`.

The plan declares `epics: [{"id": "E-01", "name": "E-01 Accounts"}]` and
`releases: [{"id": "R-01", "name": "R-01 Accounts", "stage": "bench", "stories": ["E-01.S2"]}]`.
Expected rows are then:

- **epic**: one per declared epic. Done when every story it has held is finished; the
  `building` status (or `paused`) while one of its stories is in `plans.now`; `planned` when it
  has any story; `intent` otherwise.
- **story**: the flat rows, each with its epic and (when a release lists it) its release.
- **task**: a task whose id is its story's id plus `.T<n>` (`E-01.S2.T1`). Any other task is
  listed under `not_mirrored` in `tracker.py expected`, never dropped silently.
- **release**: one per release, its status from `release_status_map`, its stage in the stage
  field when the adapter declares one.

`tracker.py diff` compares each kind only with rows of the same kind (a release tagged as a
story is a stray story and a missing release) and compares links by the work ids they name:

```
  tracker: 4 difference(s) from the plan; carry out each, then fetch the rows and diff again:
    - set Status of 'E-01.S2 Login page' to 'In review'
    - set Stage of 'E-01.S2 Login page' to 'recorded'
    - create story row: Name='E-01.S3 Logout page', Status='Backlog', Stage='intent', Updated='2026-11-25T21:28:21Z', Epic='E-01 Accounts'
    - create task row: Name='E-01.S2.T1 form', Status='In progress', Story='E-01.S2 Login page'
```

A plan that cannot be mirrored this way says why: a story in two releases, a release listing a
story the plan does not hold, a story whose epic is not declared, a task numbered under another
story, a malformed epic or release. With `meta.controller` set these FAIL; without it they are
DRIFT (at most ten lines).
