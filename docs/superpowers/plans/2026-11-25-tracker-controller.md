# Tracker Controller Implementation Plan (plan-layer 0.19.0)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One controller in plan-layer owns the plan's state fields and every list that must mirror them: it is the only writer of stage, bucket, task state and release stage, it computes one diff (plan vs its own last write, vs the tracker, vs the project's declared rules, vs a declared inventory), and that diff is a red gate fired by events, so the agent is never the trigger.

**Architecture:** The reconciliation loop (GitOps, Kubernetes controller): plan.json is the declared desired state; the controller reads the observed state (its own write stamp, the tracker rows the agent fetched, git, the files that must cover an inventory) and one function, `controller.findings(root, d, event)`, returns the diff as data. `check.py` (the gate) turns findings into FAIL lines; the existing hooks (Stop, SessionStart) and the writer scripts (`move.py`, `pause.py`, `sync.py`) call the gate with their event name. plan-layer never calls a tracker API: it computes expected rows and the diff; the agent applies them through whatever connector it has (the 0.18.0 boundary, kept).

**Tech Stack:** Python 3 standard library only; `unittest`; git CLI (read-only from the scripts).

## Global Constraints

- Stdlib only. No new dependency in any script or test.
- TDD: every task's failing test first; run from `plugins/plan-layer`: `python3 -m unittest tests/*.py`.
- Extend before building: each capability is marked EXTENDS or NEW; a NEW script names why `check.py`, `tracker.py` or `sync.py` cannot carry it.
- Opt-in, backward compatible: a plan without `meta.controller`, without `meta.tracker.relational`, without `inventory`, `epics` or `releases` gives output byte-identical to 0.18.0 (tests pin it).
- Fail loudly, never skip: an unreadable input, an unmeasurable base, an empty extraction is a FAIL with the reason, never a pass.
- No private names in code, tests, docs or examples: no product, client, agent, person or tracker link. Examples use `E-01.S2 Login page`, `agent-01`, `host-a`, `ops/backup.sh`.
- Version: plan-layer `0.19.0` in `plugins/plan-layer/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` and `plugins/plan-layer/CHANGELOG.md` (the manifest test checks they agree).
- engineering-method edits are minimal, listed in Task 10, and marked **rebase after 0.4.0** (branch `root-cause-investigation` merges first). The SKILL.md body budget is 2,200 words; measured 2,178 at base, so any SKILL.md edit is word-neutral.
- Docstrings on every new or changed function in the existing plan-layer style: what it does, why and when, inputs, output, side effects.
- Public repo, branch `tracker-controller`: commit locally, never push.

## Measured before planning (25 Nov 2026, 19:37 UTC, worktree at 5982357)

| Fact | Command | Result |
|---|---|---|
| plan-layer suite | `cd plugins/plan-layer && python3 -m unittest tests/*.py` | `Ran 246 tests in 23.813s` / `OK` |
| engineering-method budget | `python3 -m unittest tests/test_skill_budget.py`; body word count | OK; 2,178 of 2,200 words |
| No script writes stage, task state or status today | `grep -nE '\[["'"'"'](stage\|state\|status)["'"'"']\]\s*=' scripts/*.py` | no match (only `paused`, `live_revision`, `assertions_verified`, a local `revision`) |
| Hook events wired | `hooks/hooks.json` | SessionStart (`brief.py`), PreCompact (`brief.py`), Stop (`gate_hook.py`) |
| Tracker reconcile record | `plan_lib.tracker_state_path` | `plan/tracker-state.json` {at, drift, kind, plan_updated, expected_hash} |
| Template cycle | `templates/plan.json` | no `cycle` key: DEFAULT_CYCLE (intent, grounded, planned, building, verified, recorded) |
| Tests' fixture | `tests/test_light_and_budget.py` | `Base` (temp git repo, template plan), `run(script, *args, project=)`, `gate()` |

## Fit with what exists

| Capability | Exists (0.18.0) | EXTENDS / NEW | Unlocks | Goal served |
|---|---|---|---|---|
| One writer of stage, bucket, task state, release stage (S8; prose status stays hand-editable, `tracker.expected_rows` never reads it) | Single-writer precedent: `sync.py` is the only writer of `views[].spec_sha256`; `pause.py` of `meta.paused`; `plan_lib.roll` of the archive | **NEW `scripts/move.py`** (CLI writer) + **EXTENDS `plan_lib`** (writer matrix, controlled-field snapshot, stamp). Why new: `check.py` is the read-only gate (its one write is the verify stamp), `tracker.py` mirrors outward, `sync.py` orchestrates refresh-render-gate; a stage writer is its own job, like `pause.py` and `roll.py` | Stage moves become events the controller can fire rules on; the tracker sees only script-written state | Durable, trustworthy state; drift caught by code |
| The diff as data (all stories) | Gate strings in `check.run`; tracker diff in `tracker.diff_rows` | **NEW `scripts/controller.py`** (library only, no CLI). Why new: `check.run` returns strings, and `pause.py` must read the same findings structurally; putting them in `tracker.py` would make tracker-free checks (writes, rules, inventory) depend on the tracker module. Check, pause and brief all read one function | One loop, many readers; S4 and S9 add a check each, no second gate | No work built twice |
| Relational tracker reconcile (S3) | Flat rows: now, next, last 5 done; `expected`, `diff --actual`, adapters as data | **EXTENDS `tracker.py`** and the two adapters: rows gain `kind` (epic, story, task, release) and relation fields, opt-in `meta.tracker.relational`; top-level `epics[]`, `releases[]` | A tracker with linked epics, stories, tasks and releases stays correct without hand edits | Tracker shows real state |
| Drift is a red gate, run by events (S3, S7) | Tracker signals are DRIFT in `check.run`; Stop hook blocks on FAIL once per failure set | **EXTENDS `check.py`** (`--event`, findings → FAIL when `meta.controller` is set), `gate_hook.py`, `brief.py`, `sync.py`, `pause.py` pass their event; tracker signals move (unchanged text) into `controller.py` | The Stop hook blocks a turn that left the tracker unreconciled | Agent never the trigger |
| Declared rules on events (S7) | engineering-method docs-and-decisions: "a missed rule becomes a check that fails without it" (changelog entry, version bump, index line) | **EXTENDS** `controller.py` with one rule kind, `co_change` (if these paths changed since the base, these must too), bound to events; `move.py` refuses a stage move whose event rule fails | Every repeat miss of a "changed X, forgot Y" rule becomes data, not a reminder | Enforcement over instruction |
| Handoff reads the diff (S4) | `pause.py` writes HANDOFF.md from clock, git, gate | **EXTENDS `pause.py`**: a Reconcile section from `controller.findings`, git per active work id, decision ids added since the last handoff, the transcript step named | A handoff that lists what is not reconciled instead of claiming it | Next session starts true |
| Inventory parity (S9) | none | **EXTENDS** `controller.py` (one check) + schema `inventory` | "Backup covers 5 of 10 agents" and "copy job covers 1 of 2 hosts" fail the gate | Coverage proven, not assumed |

**North-star check (plugin goals):** durable state outside the context window (strengthened: state writes are attributable); verification gates (strengthened: tracker, rules and inventory are gate inputs); minimal friction (weakened, said plainly: with `meta.controller` on, a stage change blocks the end of the turn until the tracker is reconciled; that is the requested behaviour and it is opt-in); stdlib only (kept).

## Out of scope

- Calling any tracker API, storing a token, or an integration account (the agent uses its connector).
- A PostToolUse hook that catches a hand edit the moment it happens (the Stop gate catches it at turn end; add only on a measured miss).
- Rule kinds other than `co_change` (content patterns, commands, regex on files): no stated case.
- "Invariants with a runnable check" (Warp study): a co-change rule matches paths and runs nothing, so it cannot express this. plan-layer already has the mechanism, `assertions` run by `check.py --verify`, kept explicit and never hook-run by design (a hook that runs commands against the real system on every turn is the cost that ruling avoided). No new mechanism here.
- Reading the session transcript from a script; the handoff names it as the agent's step.
- Release stages as a validated enum, release-stage rules beyond the `release:<stage>` event.
- Archive view, history timeline (ROADMAP gap 1), `disputed` flag (gap 3).
- Changing engineering-method behaviour or hooks; only the two text edits in Task 10.

## File structure

| File | Change | Responsibility |
|---|---|---|
| `plugins/plan-layer/scripts/plan_lib.py` | Modify | `WRITERS` matrix, `controller_config`, `controlled`, controller-state read/write, `archived_ids` |
| `plugins/plan-layer/scripts/controller.py` | Create | `findings(root, d, event)`: one_writer, tracker, rules, inventory; `changed_files` |
| `plugins/plan-layer/scripts/move.py` | Create | The one writer of stage, task state, bucket, release stage (`--status` is a convenience, not stamped); `--adopt` |
| `plugins/plan-layer/scripts/check.py` | Modify | `--event`; tracker block moved to controller; findings into FAIL/DRIFT and `--json` |
| `plugins/plan-layer/scripts/tracker.py` | Modify | Relational expected rows, diff per kind with relations, `actual_keys` in the record |
| `plugins/plan-layer/scripts/pause.py` | Modify | Reconcile section, git per active id, decisions since last handoff |
| `plugins/plan-layer/scripts/gate_hook.py`, `brief.py`, `sync.py` | Modify | Pass their event to the gate |
| `plugins/plan-layer/trackers/notion.json`, `generic.json`, `README.md` | Modify | `relations`, `task_status_map`, `relational_fetch` |
| `plugins/plan-layer/schema/plan.schema.json` | Modify | `meta.controller`, `meta.tracker.relational`, `epics`, `releases`, `inventory` |
| `plugins/plan-layer/tests/test_controller.py` | Create | S8, S7, hook tests |
| `plugins/plan-layer/tests/test_relational.py` | Create | S3 tests |
| `plugins/plan-layer/tests/test_inventory.py` | Create | S9 tests |
| `plugins/plan-layer/tests/test_pause.py` | Modify | S4 tests |
| `plugins/plan-layer/skills/plan-layer/SKILL.md`, `README.md`, `CHANGELOG.md`, manifests | Modify | Docs, writer-matrix table, 0.19.0 |
| `plugins/engineering-method/skills/engineering-method/SKILL.md` §2 p15, `references/docs-and-decisions.md` | Modify (rebase after 0.4.0) | Point at the controller |

## Lanes and models

| Lane | Tasks | Builder | Reviewer | Region |
|---|---|---|---|---|
| A one writer | 1, 2, 3 | Opus (fresh agent per task) | Fable 5.2, one review for the lane, with executed probes | `plan_lib.py`, `controller.py`, `move.py`, `check.py`, schema `meta.controller`/`releases` |
| B relational | 4, 5 | Opus | Fable 5.2, one review for the lane | `tracker.py`, `trackers/*`, schema `meta.tracker`/`epics` |
| serial | 6, 7, 8, 9, 10 | Opus | Fable 5.2 per task (6 and 7 are the security-of-the-gate seam) | needs A and B merged |

A and B run in parallel in separate worktrees; neither needs the other's output. **Two files are shared** (review M1): `plan_lib.py` (A appends a new "Controller" section at the end; B edits only the body of `tracker_config`) and `schema/plan.schema.json` (A adds `meta.controller` and `releases`; B adds `meta.tracker.relational` and `epics`). Merge order: **A first** into `tracker-controller`; then B rebases onto it, resolves the two files by keeping both sides, runs `tests/test_controller.py`, `tests/test_relational.py` and `tests/test_tracker.py`, and merges; the controller then runs the full suite before Task 6 starts. Every agent reports the model id it ran as. Implementers do not run the full suite; the controller does after each merge. Bound: 60 tool calls per implementer task, then "stop and report".

---

### Task 1: Writer matrix, controller config, controlled-field stamp (S8, plumbing)

**Files:**
- Modify: `plugins/plan-layer/scripts/plan_lib.py` (append a "Controller" section after the tracker section)
- Modify: `plugins/plan-layer/schema/plan.schema.json` (`meta.controller`, top-level `releases`)
- Test: `plugins/plan-layer/tests/test_controller.py` (create)

**Interfaces:**
- Produces:
  - `L.WRITERS: list[dict]` each `{"field": str, "writer": str, "enforced": str}`
  - `L.controller_config(d) -> (dict | None, str | None)`; dict `{"one_writer": bool, "base": str, "decision_log": str | None, "rules": list}`; `(None, None)` when `meta.controller` is absent
  - `L.controlled(d) -> {"items": {wid: {"bucket", "stage", "tasks": {name: state}}}, "releases": {rid: stage}}` (prose status is not controlled: ruling 2)
  - `L.duplicate_ids(d) -> list[str]` (work ids held by more than one live item; I4)
  - `L.controller_state(root) -> dict | None`, `L.write_stamp(root, d, by) -> None`, `L.controller_state_path(root) -> str`, `L.archived_ids(root) -> set[str]`

- [ ] **Step 1: Write the failing tests**

```python
"""Tracker controller (0.19.0): one writer, the diff as data, rules on events."""
import json
import os
import subprocess
import sys
import unittest
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_light_and_budget import Base, PLUGIN, SCRIPTS, run  # noqa: E402
import plan_lib as L  # noqa: E402


def item(name, stage="intent", **kw):
    d = {"name": name, "why": "w", "unblocks": "u", "stage": stage, "plan_file": None}
    d.update(kw)
    return d


def ctl(msgs):
    return [m for m in msgs if "move.py" in m or "meta.controller" in m or "by hand" in m]


class ControllerBase(Base):
    def setUp(self):
        super().setUp()
        self.d["meta"]["naming"] = "work-ids"
        self.d["meta"]["controller"] = {"one_writer": True}
        self.d["plans"]["now"] = [item("E-01.S2 Login page", "building", plan_file="docs/p.md",
                                       status="wiring the form", updated="2026-01-01",
                                       tasks=[{"name": "E-01.S2.T1 form", "state": "todo"}])]
        self.d["plans"]["next"] = [item("E-01.S3 Logout page")]
        self.d["plans"]["done"] = []

    def move(self, *args):
        return run("move.py", *args, project=self.dir)

    def stamp(self):
        p = os.path.join(self.dir, "plan", "controller-state.json")
        return json.load(open(p)) if os.path.isfile(p) else None


class TestPlumbing(ControllerBase):
    def test_config_absent_is_off(self):
        del self.d["meta"]["controller"]
        self.assertEqual(L.controller_config(self.d), (None, None))

    def test_config_defaults(self):
        cfg, err = L.controller_config(self.d)
        self.assertIsNone(err)
        self.assertEqual(cfg, {"one_writer": True, "base": "main", "decision_log": None, "rules": []})

    def test_config_faults_are_words(self):
        for bad, word in (([], "object"), ({"one_writer": "yes"}, "true or false"),
                          ({"surprise": 1}, "unknown"), ({"base": ""}, "base"),
                          ({"rules": {}}, "rules")):
            self.d["meta"]["controller"] = bad
            cfg, err = L.controller_config(self.d)
            self.assertIsNone(cfg, bad)
            self.assertIn(word, err, bad)

    def test_one_writer_needs_work_id_naming(self):
        del self.d["meta"]["naming"]
        cfg, err = L.controller_config(self.d)
        self.assertIn("work-ids", err)

    def test_controlled_reads_bucket_stage_tasks_and_releases_not_status(self):
        self.d["releases"] = [{"id": "R-01", "name": "R-01 Accounts", "stage": "build",
                               "stories": ["E-01.S2"]}]
        c = L.controlled(self.d)
        s2 = c["items"]["E-01.S2"]
        self.assertEqual(s2, {"bucket": "now", "stage": "building",
                              "tasks": {"E-01.S2.T1 form": "todo"}})
        self.assertEqual(c["releases"], {"R-01": "build"})

    def test_duplicate_live_work_ids_are_found(self):
        self.assertEqual(L.duplicate_ids(self.d), [])
        self.d["plans"]["next"].append(item("E-01.S2 Login page, again"))
        self.assertEqual(L.duplicate_ids(self.d), ["E-01.S2"])

    def test_write_stamp_round_trips_and_keeps_other_keys(self):
        self.write()
        path = L.controller_state_path(self.dir)
        with open(path, "w") as fh:
            json.dump({"adopted": [{"at": "x"}]}, fh)
        L.write_stamp(self.dir, self.d, "move.py E-01.S2 --stage building")
        st = L.controller_state(self.dir)
        self.assertEqual(st["adopted"], [{"at": "x"}])
        self.assertEqual(st["writes"]["by"], "move.py E-01.S2 --stage building")
        self.assertEqual(st["writes"]["items"], L.controlled(self.d)["items"])
        self.assertTrue(st["writes"]["at"].endswith("Z"))

    def test_writer_matrix_names_every_stamped_field(self):
        fields = " ".join(w["field"] for w in L.WRITERS)
        for f in ("stage", "tasks[].state", "releases[].stage", "meta.paused",
                  "plan/tracker-state.json", "plan/controller-state.json"):
            self.assertIn(f, fields)
        for w in L.WRITERS:
            self.assertTrue(w["writer"] and w["enforced"], w)
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd plugins/plan-layer && python3 -m unittest tests/test_controller.py -v`
Expected: FAIL / ERROR with `AttributeError: module 'plan_lib' has no attribute 'controller_config'`.

- [ ] **Step 3: Implement in `plan_lib.py`**

```python
# --------------------------------------------------------------------------
# Controller (0.19.0). The reconciliation loop: plan.json is the desired state,
# one writer moves its state fields, and controller.findings() is the one diff.
# The writer matrix is data so the skill's table and the code cannot disagree.
CONTROLLER_STATE_FILENAME = "controller-state.json"
_CONTROLLER_KEYS = ("one_writer", "base", "decision_log", "rules")

WRITERS = [
    {"field": "plans.now[] / plans.next[]: membership, stage, tasks[].state",
     "writer": "move.py", "enforced": "stamp in plan/controller-state.json; the gate FAILs on a hand edit"},
    {"field": "plans.done[] (an item finished from now)", "writer": "move.py --to done",
     "enforced": "stamp"},
    {"field": "releases[].stage", "writer": "move.py", "enforced": "stamp"},
    {"field": "meta.paused, plan/HANDOFF.md", "writer": "pause.py", "enforced": "sole code path (test)"},
    {"field": "views[].spec_sha256, views[].revision, facts.live_revision", "writer": "sync.py",
     "enforced": "sole code path"},
    {"field": "meta.assertions_verified", "writer": "check.py --verify", "enforced": "sole code path"},
    {"field": "plan/archive/*.json", "writer": "plan_lib.roll (roll.py, sync.py)", "enforced": "sole code path"},
    {"field": "plan/tracker-state.json", "writer": "tracker.py diff, sync.py --tracker --actual",
     "enforced": "sole code path"},
    {"field": "plan/controller-state.json", "writer": "plan_lib.write_stamp (move.py)",
     "enforced": "sole code path"},
    {"field": "plan/index.html", "writer": "render.py", "enforced": "fingerprint"},
]


def controller_config(d):
    """meta.controller resolved, or (None, None) when absent. Returns (config, error); one is None.

    Why: check.py, move.py and pause.py must read one effective config. Every
    fault is words, never a silent default. one_writer keys items by work id,
    so it requires meta.naming = "work-ids". Rules are validated in
    controller.rule_faults (they need the cycle's stage ids). No side effects.
    """
    meta = d.get("meta") or {}
    if "controller" not in meta:
        return None, None
    c = meta["controller"]
    if not isinstance(c, dict):
        return None, "meta.controller is %r — it must be an object" % (c,)
    unknown = sorted(set(c) - set(_CONTROLLER_KEYS))
    if unknown:
        return None, "meta.controller has unknown key(s) %s (known: %s)" % (
            ", ".join(unknown), ", ".join(_CONTROLLER_KEYS))
    ow = c.get("one_writer", False)
    if not isinstance(ow, bool):
        return None, "meta.controller.one_writer is %r — it must be true or false" % (ow,)
    if ow and meta.get("naming") != "work-ids":
        return None, ("meta.controller.one_writer keys items by work id — set meta.naming "
                      "to \"work-ids\"")
    base = c.get("base", "main")
    if not isinstance(base, str) or not base.strip():
        return None, "meta.controller.base is %r — it must name the base branch" % (base,)
    log = c.get("decision_log")
    if log is not None and not (isinstance(log, str) and log.strip()):
        return None, "meta.controller.decision_log is %r — a path, or leave it out" % (log,)
    rules = c.get("rules", [])
    if not isinstance(rules, list):
        return None, "meta.controller.rules is %r — it must be a list" % (rules,)
    return {"one_writer": ow, "base": base, "decision_log": log, "rules": rules}, None


def controlled(d):
    """The fields one writer owns, read from the plan. Pure.

    Items in plans.now and plans.next keyed by work id (an item without one is
    the naming check's FAIL, not this one's); releases[] keyed by id. Prose
    status is deliberately not controlled: nothing downstream reads it as
    state (review ruling 2). Two live items with one id collapse here, so
    duplicate_ids() is checked first and FAILs.
    """
    out = {"items": {}, "releases": {}}
    plans = d.get("plans") or {}
    for bucket in ("now", "next"):
        for it in plans.get(bucket) or []:
            wid = work_id(it.get("name")) if isinstance(it, dict) else None
            if not wid:
                continue
            out["items"][wid] = {
                "bucket": bucket, "stage": it.get("stage"),
                "tasks": {str(t.get("name")): t.get("state")
                          for t in it.get("tasks") or [] if isinstance(t, dict)}}
    for r in d.get("releases") or []:
        if isinstance(r, dict) and work_id(r.get("id")):
            out["releases"][r["id"]] = r.get("stage")
    return out


def duplicate_ids(d):
    """Work ids carried by more than one item in plans.now and plans.next, sorted. Pure."""
    seen, dup = set(), set()
    for bucket in ("now", "next"):
        for it in (d.get("plans") or {}).get(bucket) or []:
            wid = work_id(it.get("name")) if isinstance(it, dict) else None
            if wid in seen:
                dup.add(wid)
            elif wid:
                seen.add(wid)
    return sorted(dup)


def controller_state_path(root=None):
    """Where the controller records its last write: <plan dir>/controller-state.json."""
    return os.path.join(paths(root)["dir"], CONTROLLER_STATE_FILENAME)


def controller_state(root=None):
    """The controller record, or None when absent or unreadable."""
    try:
        v = json.load(open(controller_state_path(root), encoding="utf-8"))
        return v if isinstance(v, dict) else None
    except Exception:
        return None


def write_stamp(root, d, by):
    """Record what the one writer just wrote. Side effect: rewrites controller-state.json's "writes".

    Other keys (adopted, handoff) are kept. `by` is the command line that wrote it.
    """
    st = controller_state(root) or {}
    st["writes"] = dict(controlled(d), at=utc_now(), by=by)
    atomic_write(controller_state_path(root), json.dumps(st, indent=2, ensure_ascii=False) + "\n")


def archived_ids(root=None):
    """Work ids held in plan/archive/done.json and backlog.json (rolled, so not 'gone by hand')."""
    out = set()
    adir = os.path.join(paths(root)["dir"], ARCHIVE_DIRNAME)
    for fn in ("done.json", "backlog.json"):
        try:
            for it in json.load(open(os.path.join(adir, fn), encoding="utf-8")) or []:
                wid = work_id(it.get("name")) if isinstance(it, dict) else None
                if wid:
                    out.add(wid)
        except Exception:
            continue
    return out
```

Schema: add `meta.controller` (object: `one_writer` boolean, `base` string, `decision_log` string, `rules` array, `additionalProperties: false`, description naming the writer matrix and `move.py`), and top-level `releases` (array of `{id: "R-NN", name, stage, stories: [story ids]}`, required `id`, `name`, `stage`).

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m unittest tests/test_controller.py -v`
Expected: 8 tests OK.

- [ ] **Step 5: Commit**

```bash
git add plugins/plan-layer/scripts/plan_lib.py plugins/plan-layer/schema/plan.schema.json plugins/plan-layer/tests/test_controller.py
git commit -m "plan-layer: writer matrix, meta.controller and the controlled-field stamp (S8)"
```

---

### Task 2: `controller.findings` with the one-writer check; the gate reads it (S8)

**Files:**
- Create: `plugins/plan-layer/scripts/controller.py`
- Modify: `plugins/plan-layer/scripts/check.py` (`run(root=None, event=None)`, `main` parses `--event`, `--json` gains `"controller"` only when opted in)
- Modify: `plugins/plan-layer/tests/test_plan_layer.py:1394` (`allowed` gains `"controller"`)
- Test: `plugins/plan-layer/tests/test_controller.py` (append)

**Interfaces:**
- Consumes: Task 1's `L.controller_config`, `L.controlled`, `L.controller_state`, `L.archived_ids`.
- Produces: `controller.findings(root, d, event=None) -> list[dict]`, each `{"check": "config"|"one_writer"|"tracker"|"rule"|"inventory", "level": "FAIL"|"DRIFT", "message": str}`; `controller.first_stage(d) -> str`; `check.run(root=None, event=None)`; `check.py --event <name>`.

- [ ] **Step 1: Write the failing tests**

```python
def stamp_now(test):
    """Stamp the plan as move.py would, without move.py (Task 3 builds it)."""
    test.write()
    L.write_stamp(test.dir, test.d, "test")


class TestOneWriterGate(ControllerBase):
    def test_off_without_controller(self):
        del self.d["meta"]["controller"]
        self.write()
        _, fails, drifts = self.gate()
        self.assertEqual(ctl(fails + drifts), [])

    def test_on_without_stamp_fails_and_says_adopt(self):
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue(any("move.py --adopt" in f for f in fails), fails)

    def test_clean_after_stamp(self):
        stamp_now(self)
        _, fails, _ = self.gate()
        self.assertEqual(ctl(fails), [], fails)

    def test_hand_edit_of_stage_fails_naming_item_field_and_writer(self):
        stamp_now(self)
        self.d["plans"]["now"][0]["stage"] = "verified"
        self.write()
        rc, fails, _ = self.gate()
        self.assertEqual(rc, 1)
        hit = [f for f in fails if "E-01.S2" in f and "stage" in f and "by hand" in f]
        self.assertTrue(hit, fails)
        self.assertIn("move.py E-01.S2 --stage verified", hit[0])

    def test_hand_edit_of_task_state_fails_but_prose_status_is_free(self):
        stamp_now(self)
        self.d["plans"]["now"][0]["status"] = "rewritten by hand"
        self.write()
        _, fails, _ = self.gate()
        self.assertEqual(ctl(fails), [], "prose status is not controlled (ruling 2)")
        self.d["plans"]["now"][0]["tasks"][0]["state"] = "done"
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue(any("E-01.S2.T1 form" in f and "done" in f for f in fails), fails)

    def test_two_live_items_with_one_work_id_fail(self):
        stamp_now(self)
        self.d["plans"]["next"].append(item("E-01.S2 Login page, again"))
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue(any("E-01.S2" in f and "more than one" in f for f in fails), fails)

    def test_json_has_no_controller_key_when_off(self):
        del self.d["meta"]["controller"]
        self.write()
        run("render.py", project=self.dir)
        out = json.loads(run("check.py", "--json", project=self.dir).stdout)
        self.assertNotIn("controller", out)
        self.assertNotIn("controller", out["summary"])

    def test_a_crash_inside_the_controller_is_a_fail_not_silence(self):
        stamp_now(self)
        with open(L.controller_state_path(self.dir), "w") as fh:
            json.dump({"writes": {"items": {"E-01.S2": "not-a-dict"}}}, fh)
        _, fails, _ = self.gate()
        self.assertTrue(any("controller crashed" in f for f in fails), fails)

    def test_new_idea_in_next_at_first_stage_is_planning_not_a_hand_move(self):
        stamp_now(self)
        self.d["plans"]["next"].append(item("E-01.S4 Profile page"))
        self.write()
        _, fails, _ = self.gate()
        self.assertEqual(ctl(fails), [], fails)

    def test_new_item_straight_into_now_fails(self):
        stamp_now(self)
        self.d["plans"]["now"].append(item("E-02.S1 Search", "building", status="s", updated="u",
                                           plan_file="docs/q.md"))
        self.d["meta"]["allow_multiple_active"] = True
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue(any("E-02.S1" in f and "plans.now" in f for f in fails), fails)

    def test_hand_move_to_done_fails_but_a_roll_does_not(self):
        stamp_now(self)
        s2 = self.d["plans"]["now"].pop(0)
        self.d["plans"]["done"].append({"name": s2["name"], "period": "2026-01-02", "outcome": "o"})
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue(any("E-01.S2" in f and "left" in f for f in fails), fails)
        os.makedirs(os.path.join(self.dir, "plan", "archive"), exist_ok=True)
        with open(os.path.join(self.dir, "plan", "archive", "done.json"), "w") as fh:
            json.dump([{"name": s2["name"]}], fh)
        self.d["plans"]["done"] = []
        self.write()
        _, fails, _ = self.gate()
        self.assertEqual([f for f in fails if "E-01.S2" in f and "left" in f], [], fails)

    def test_release_stage_hand_edit_fails(self):
        self.d["releases"] = [{"id": "R-01", "name": "R-01 Accounts", "stage": "build", "stories": []}]
        stamp_now(self)
        self.d["releases"][0]["stage"] = "production"
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue(any("R-01" in f and "move.py R-01 --stage production" in f for f in fails), fails)

    def test_bad_config_is_a_fail(self):
        self.d["meta"]["controller"] = {"one_writer": "yes"}
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue(any("meta.controller.one_writer" in f for f in fails), fails)

    def test_json_output_carries_structured_findings(self):
        self.write()
        run("render.py", project=self.dir)
        r = run("check.py", "--json", project=self.dir)
        out = json.loads(r.stdout)
        self.assertTrue(any(f["check"] == "one_writer" and f["level"] == "FAIL"
                            for f in out["controller"]), out.get("controller"))

    def test_event_flag_is_accepted_and_unknown_flag_value_is_usage(self):
        stamp_now(self)
        run("render.py", project=self.dir)
        self.assertEqual(run("check.py", "--event", "stop", project=self.dir).returncode, 0)
        self.assertEqual(run("check.py", "--event", project=self.dir).returncode, 2)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest tests/test_controller.py -v`
Expected: the new tests FAIL (no `controller` module; `--event` unknown; no `"controller"` key).

- [ ] **Step 3: Create `scripts/controller.py`**

```python
#!/usr/bin/env python3
"""The controller's one diff: desired state (the plan) against observed state.

The reconciliation-loop pattern (GitOps, a Kubernetes controller): one function
reads the declared state and what is observed, and returns every difference as
data. The gate (check.py) prints them as FAIL or DRIFT; pause.py writes them
into the handoff; the hooks fire them by event. Nothing here writes, sends or
calls a network: the agent applies tracker fixes through its own connector.

  findings(root, d, event=None) -> [{"check", "level", "message"}]

Checks: config (meta.controller well formed), one_writer (state changed only by
move.py), tracker (Task 6), rule (Task 7, only on the rule's events),
inventory (Task 9). Library only: there is no CLI; read it with check.py --json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_lib as L  # noqa: E402


def _f(check, message, level="FAIL"):
    return {"check": check, "level": level, "message": message}


def first_stage(d):
    """The cycle's first stage id ('intent' by default): where a new idea enters."""
    stages = (d.get("cycle") or L.DEFAULT_CYCLE).get("stages") or [{}]
    return stages[0].get("id")


def one_writer_findings(root, d, cfg):
    """Every controlled field that differs from move.py's last recorded write.

    Inputs: root, plan dict, controller config. Output: list of findings.
    Allowed without move.py, because they are planning, not progress: a new
    item in plans.next at the first stage with every task todo; a queued item
    at the first stage removed; any item that rolled into plan/archive/.
    Everything else is a hand edit and FAILs with the exact move.py command.
    """
    if not cfg or not cfg["one_writer"]:
        return []
    st = L.controller_state(root) or {}
    rec = st.get("writes")
    if not isinstance(rec, dict):
        return [_f("one_writer", "meta.controller.one_writer is on but move.py has recorded no write — "
                   "run move.py --adopt once to stamp the current state")]
    dups = L.duplicate_ids(d)
    if dups:
        return [_f("one_writer", "%s is the work id of more than one live item — give each its own id"
                   % w) for w in dups]
    cur, first = L.controlled(d), first_stage(d)
    archived = L.archived_ids(root)
    out = []
    ritems, citems = rec.get("items") or {}, cur["items"]
    for wid in sorted(set(ritems) | set(citems)):
        a, b = ritems.get(wid), citems.get(wid)
        if a and b:
            if a["bucket"] != b["bucket"]:
                out.append(_f("one_writer", "%s moved from plans.%s to plans.%s by hand — run "
                              "move.py %s --to %s" % (wid, a["bucket"], b["bucket"], wid, b["bucket"])))
            if a["stage"] != b["stage"]:
                out.append(_f("one_writer", "stage of %s is %r but move.py last wrote %r — changed by hand; "
                              "run move.py %s --stage %s (or revert the edit)"
                              % (wid, b["stage"], a["stage"], wid, b["stage"])))
            for t in sorted(set(a["tasks"]) | set(b["tasks"])):
                ta, tb = a["tasks"].get(t), b["tasks"].get(t)
                if ta is None and tb != "todo":
                    out.append(_f("one_writer", "task %r of %s entered at %r by hand — add it as todo, then "
                                  "move.py %s --task %r --state %s" % (t, wid, tb, wid, t, tb)))
                elif tb is None and ta not in (None, "todo"):
                    out.append(_f("one_writer", "task %r of %s (%s) was removed by hand" % (t, wid, ta)))
                elif ta is not None and tb is not None and ta != tb:
                    out.append(_f("one_writer", "task %r of %s is %r but move.py last wrote %r — changed by "
                                  "hand; run move.py %s --task %r --state %s" % (t, wid, tb, ta, wid, t, tb)))
        elif b:
            if not (b["bucket"] == "next" and b["stage"] == first
                    and all(s == "todo" for s in b["tasks"].values())):
                out.append(_f("one_writer", "%s entered plans.%s at stage %r by hand — add it to plans.next "
                              "at %r, then move it with move.py" % (wid, b["bucket"], b["stage"], first)))
        elif wid not in archived and not (a["bucket"] == "next" and a["stage"] == first):
            out.append(_f("one_writer", "%s left plans.%s by hand (it was at %r) — finish it with "
                          "move.py %s --to done --outcome \"<text>\", or restore it"
                          % (wid, a["bucket"], a["stage"], wid)))
    rrel = rec.get("releases") or {}
    for rid, stage in sorted(cur["releases"].items()):
        if rid in rrel and rrel[rid] != stage:
            out.append(_f("one_writer", "stage of %s is %r but move.py last wrote %r — changed by hand; "
                          "run move.py %s --stage %s" % (rid, stage, rrel[rid], rid, stage)))
    return out


def findings(root, d, event=None):
    """The whole diff, in check order. Inputs: root, plan dict, event name or None. Pure reads."""
    cfg, err = L.controller_config(d)
    if err:
        return [_f("config", err)]
    return one_writer_findings(root, d, cfg)
```

In `check.py`: `import controller` beside `import tracker`; change `def run(root=None):` to `def run(root=None, event=None):`; just before `log = d.get("meta", {}).get("changelog", [])`, add:

```python
    # The controller's diff (0.19.0): one function, read by the gate, the
    # handoff and the hooks, so nothing computes it twice. A crash inside it
    # is a FAIL, never silence: the Stop hook fails open on an exception, so
    # an uncaught one would switch the whole gate off (review I3).
    try:
        found = controller.findings(root, d, event)
    except Exception as exc:
        found = [{"check": "config", "level": "FAIL",
                  "message": "controller crashed (%s: %s) — the plan's controller inputs are malformed"
                             % (exc.__class__.__name__, exc)}]
    for f in found:
        (fails if f["level"] == "FAIL" else drifts).append(f["message"])
    controller_on = "controller" in d.get("meta", {}) or "inventory" in d
```

after `summary` is built, add `if controller_on: summary["controller"] = found` (absent otherwise, so `--json` stays byte-identical for a plan that does not opt in: review M2); in `main`:

```python
    event = None
    if "--event" in sys.argv:
        i = sys.argv.index("--event")
        if i + 1 >= len(sys.argv) or sys.argv[i + 1].startswith("--"):
            print("  usage: check.py --event <stop|session-start|sync|pause|stage:<id>|release:<stage>>")
            return 2
        event = sys.argv[i + 1]
    fails, drifts, summary = run(event=event)
```

and in the `--json` branch add `"controller": summary["controller"]` only when the key is in `summary`.

Add `"controller"` to the `allowed` set in `tests/test_plan_layer.py::test_no_third_party_imports` (line 1394 at base), or that test fails on the new import (review I1). Update the module docstring's usage block with `check.py --event <name>`.

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m unittest tests/test_controller.py -v`
Expected: all OK. Then `python3 -m unittest tests/*.py` from the controller only after merge (implementers skip it).

- [ ] **Step 5: Commit**

```bash
git add plugins/plan-layer/scripts/controller.py plugins/plan-layer/scripts/check.py plugins/plan-layer/tests/test_controller.py plugins/plan-layer/tests/test_plan_layer.py
git commit -m "plan-layer: controller.findings, the one diff; the gate FAILs on a hand edit of stage or task state (S8)"
```

---

### Task 3: `move.py`, the one writer (S8)

**Files:**
- Create: `plugins/plan-layer/scripts/move.py`
- Test: `plugins/plan-layer/tests/test_controller.py` (append)

**Interfaces:**
- Consumes: `L.write_stamp`, `L.controller_config`, `controller.one_writer_findings`, `controller.first_stage`.
- Produces: CLI
  - `move.py <id> --stage <stage> [--status TEXT]` (item stage must be a cycle stage; a release stage any non-empty text)
  - `move.py <id> --status TEXT`
  - `move.py <id> --task <name or task id> --state done|active|todo|blocked`
  - `move.py <id> --to now|next|done [--status TEXT] [--outcome TEXT]` (`now` needs a status, given or present; `done` needs `--outcome`)
  - `move.py --adopt` (stamp the current state; record what it accepted)
  - Exit 0 written; 1 refused (pending hand edits, review C1; or, Task 7, a rule on the event failed); 2 usage, unknown id, invalid stage or state, a non-stage flag on a release (M3).
  - `--status` writes the prose status as a convenience; it is not stamped (ruling 2).
  - `move.event_for(kind, stage) -> str` (`"stage:<id>"` for items, `"release:<stage>"` for releases), used by Task 7.

- [ ] **Step 1: Write the failing tests**

```python
class TestMove(ControllerBase):
    def setUp(self):
        super().setUp()
        stamp_now(self)

    def test_stage_move_writes_stamps_bumps_and_renders(self):
        r = self.move("E-01.S2", "--stage", "verified", "--status", "suite green")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        d = self.read()
        self.assertEqual(d["plans"]["now"][0]["stage"], "verified")
        self.assertEqual(d["plans"]["now"][0]["status"], "suite green")
        self.assertNotEqual(d["meta"]["updated"], "2026-01-01T00:00:00Z")
        self.assertEqual(self.stamp()["writes"]["items"]["E-01.S2"]["stage"], "verified")
        self.assertIn("building -> verified", r.stdout)
        _, fails, _ = self.gate()
        self.assertEqual(ctl(fails), [], fails)

    def test_task_state_by_task_id_or_full_name(self):
        self.assertEqual(self.move("E-01.S2", "--task", "E-01.S2.T1", "--state", "done").returncode, 0)
        self.assertEqual(self.read()["plans"]["now"][0]["tasks"][0]["state"], "done")
        self.assertEqual(self.move("E-01.S2", "--task", "E-01.S2.T1 form", "--state", "active").returncode, 0)

    def test_to_now_then_done(self):
        self.d = self.read()
        self.d["meta"]["allow_multiple_active"] = True
        self.write()
        L.write_stamp(self.dir, self.d, "test")
        self.assertEqual(self.move("E-01.S3", "--to", "now").returncode, 2, "now needs a status")
        self.assertEqual(self.move("E-01.S3", "--to", "now", "--status", "starting").returncode, 0)
        r = self.move("E-01.S2", "--to", "done", "--outcome", "login works")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        d = self.read()
        self.assertEqual([p["name"] for p in d["plans"]["now"]], ["E-01.S3 Logout page"])
        self.assertEqual(d["plans"]["done"][-1]["outcome"], "login works")
        self.assertNotIn("E-01.S2", self.stamp()["writes"]["items"])
        _, fails, _ = self.gate()
        self.assertEqual(ctl(fails), [], fails)

    def test_release_stage(self):
        self.d = self.read()
        self.d["releases"] = [{"id": "R-01", "name": "R-01 Accounts", "stage": "build", "stories": []}]
        self.write()
        L.write_stamp(self.dir, self.d, "test")
        self.assertEqual(self.move("R-01", "--stage", "production").returncode, 0)
        self.assertEqual(self.read()["releases"][0]["stage"], "production")

    def test_refusals_are_exit_2_and_change_nothing(self):
        before = open(os.path.join(self.dir, "plan", "plan.json")).read()
        for args in (("E-09.S1", "--stage", "building"), ("E-01.S2", "--stage", "flying"),
                     ("E-01.S2", "--task", "nope", "--state", "done"),
                     ("E-01.S2", "--task", "E-01.S2.T1", "--state", "finished"),
                     ("E-01.S2", "--to", "done"), ("E-01.S2",), ()):
            r = self.move(*args)
            self.assertEqual(r.returncode, 2, (args, r.stdout + r.stderr))
        self.assertEqual(open(os.path.join(self.dir, "plan", "plan.json")).read(), before)

    def test_adopt_records_what_it_accepted(self):
        self.d = self.read()
        self.d["plans"]["now"][0]["stage"] = "verified"
        self.write()
        r = self.move("--adopt")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("stage of E-01.S2", r.stdout)
        st = self.stamp()
        self.assertEqual(len(st["adopted"]), 1)
        self.assertIn("stage of E-01.S2", st["adopted"][0]["changes"][0])
        _, fails, _ = self.gate()
        self.assertEqual(ctl(fails), [], fails)

    def test_pending_hand_edit_blocks_any_move_and_is_not_adopted(self):
        self.d = self.read()
        self.d["plans"]["now"][0]["stage"] = "verified"
        self.write()
        r = self.move("E-01.S3", "--stage", "grounded")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("pending hand edits", r.stdout)
        self.assertEqual(self.read()["plans"]["next"][0]["stage"], "intent", "nothing written")
        self.assertEqual(self.stamp()["writes"]["items"]["E-01.S2"]["stage"], "building",
                         "the hand edit was not silently adopted")

    def test_release_takes_stage_only(self):
        self.d = self.read()
        self.d["releases"] = [{"id": "R-01", "name": "R-01 Accounts", "stage": "build", "stories": []}]
        self.write()
        L.write_stamp(self.dir, self.d, "test")
        for args in (("--status", "x"), ("--to", "now"), ("--task", "T", "--state", "done")):
            r = self.move("R-01", *args)
            self.assertEqual(r.returncode, 2, (args, r.stdout + r.stderr))
            self.assertIn("releases take --stage only", r.stdout)

    def test_tracker_reminder_when_a_tracker_is_set(self):
        self.d = self.read()
        self.d["meta"]["tracker"] = {"kind": "notion", "target": "db-1"}
        self.write()
        L.write_stamp(self.dir, self.d, "test")
        r = self.move("E-01.S2", "--stage", "verified")
        self.assertIn("sync.py --tracker", r.stdout)


class TestSoleWriter(unittest.TestCase):
    """The writer matrix is enforced in code: no other script assigns a stamped field."""
    def test_only_move_and_plan_lib_assign_stage_or_state(self):
        import re
        pat = re.compile(r"""\[["'](stage|state)["']\]\s*=(?!=)""")
        for fn in sorted(os.listdir(SCRIPTS)):
            if fn.endswith(".py") and fn not in ("move.py", "plan_lib.py"):
                text = open(os.path.join(SCRIPTS, fn), encoding="utf-8").read()
                self.assertIsNone(pat.search(text), fn)

    def test_only_pause_assigns_meta_paused(self):
        import re
        pat = re.compile(r"""\[["']paused["']\]\s*=(?!=)""")
        for fn in sorted(os.listdir(SCRIPTS)):
            if fn.endswith(".py") and fn != "pause.py":
                self.assertIsNone(pat.search(open(os.path.join(SCRIPTS, fn)).read()), fn)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest tests/test_controller.py -v`
Expected: TestMove errors (`move.py` not found, non-zero exit), TestSoleWriter passes already (it pins the matrix; it must still pass after move.py lands).

- [ ] **Step 3: Create `scripts/move.py`**

```python
#!/usr/bin/env python3
"""The one writer of plan state: stage, task state, bucket, release stage (and, as a convenience, status).

  move.py <id> --stage <stage> [--status TEXT]
  move.py <id> --status TEXT
  move.py <id> --task <name or task id> --state done|active|todo|blocked
  move.py <id> --to now|next|done [--status TEXT] [--outcome TEXT]
  move.py --adopt        stamp the current state (first opt-in, or after a human's deliberate edit)

Why: with meta.controller.one_writer on, the gate FAILs on any controlled field
that differs from this script's last recorded write, so a stage the tracker,
the brief and the handoff read is always one a script wrote. A stage move is an
event: rules bound to it run first and a failing rule refuses the move.

Side effects: rewrites plan/plan.json (the field, the item's `updated`,
meta.updated), plan/controller-state.json (the stamp), re-renders the page.
Exit: 0 written, 1 refused by a rule, 2 usage / unknown id / invalid value.
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_lib as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TASK_STATES = ("done", "active", "todo", "blocked")


class Usage(Exception):
    """A request move.py will not write; the message says why (exit 2)."""


def event_for(kind, stage):
    """The event a move fires: stage:<id> for an item, release:<stage> for a release."""
    return ("release:%s" if kind == "release" else "stage:%s") % stage


def find(d, wid):
    """(kind, bucket, object) for a work id in now, next or releases; raises Usage when absent."""
    for bucket in ("now", "next"):
        for it in (d.get("plans") or {}).get(bucket) or []:
            if L.work_id(it.get("name")) == wid:
                return "item", bucket, it
    for r in d.get("releases") or []:
        if r.get("id") == wid:
            return "release", None, r
    raise Usage("%s is not in plans.now, plans.next or releases" % wid)


def apply(d, a):
    """Apply the request to d in memory. Returns (description, event or None). Raises Usage."""
    kind, bucket, obj = find(d, a.id)
    if kind == "release" and (a.status is not None or a.task or a.to):
        raise Usage("releases take --stage only")
    stages = [s["id"] for s in (d.get("cycle") or L.DEFAULT_CYCLE)["stages"]]
    today = L.utc_now()[:10]
    said, event = [], None
    if a.stage:
        if kind == "item" and a.stage not in stages:
            raise Usage("stage %r is not a cycle stage (%s)" % (a.stage, ", ".join(stages)))
        if not a.stage.strip():
            raise Usage("a release stage cannot be empty")
        said.append("%s %s -> %s" % (a.id, obj.get("stage"), a.stage))
        obj["stage"], event = a.stage, event_for(kind, a.stage)
    if a.status is not None:
        if kind != "item" or not a.status.strip():
            raise Usage("--status takes non-empty text and applies to plan items")
        obj["status"] = a.status
        said.append("%s status set" % a.id)
    if a.task:
        if a.state not in TASK_STATES:
            raise Usage("--state must be one of %s" % ", ".join(TASK_STATES))
        hits = [t for t in obj.get("tasks") or [] if t.get("name") == a.task
                or L.work_id(t.get("name")) == a.task]
        if len(hits) != 1:
            raise Usage("task %r matches %d tasks of %s" % (a.task, len(hits), a.id))
        said.append("task %r %s -> %s" % (hits[0]["name"], hits[0].get("state"), a.state))
        hits[0]["state"] = a.state
    if a.to:
        plans = d["plans"]
        if a.to == "done":
            if not (a.outcome and a.outcome.strip()):
                raise Usage("--to done needs --outcome \"<what it produced>\"")
            plans[bucket].remove(obj)
            plans.setdefault("done", []).append(
                {k: v for k, v in (("name", obj["name"]), ("period", today), ("outcome", a.outcome),
                                   ("file", obj.get("plan_file")), ("capability", obj.get("capability")),
                                   ("stage", "recorded")) if v is not None})
        elif a.to != bucket:
            if a.to == "now" and not (obj.get("status") or "").strip():
                raise Usage("--to now needs --status: an active item says where it stands")
            plans[bucket].remove(obj)
            plans.setdefault(a.to, []).append(obj)
        said.append("%s plans.%s -> plans.%s" % (a.id, bucket, a.to))
    if not said:
        raise Usage("nothing to move: give --stage, --status, --task/--state or --to")
    if kind == "item" and a.to != "done":
        obj["updated"] = today
    return "; ".join(said), event


def main():
    ap = argparse.ArgumentParser(prog="move.py", description=__doc__.split("\n")[0])
    ap.add_argument("id", nargs="?")
    ap.add_argument("--stage")
    ap.add_argument("--status")
    ap.add_argument("--task")
    ap.add_argument("--state")
    ap.add_argument("--to", choices=("now", "next", "done"))
    ap.add_argument("--outcome")
    ap.add_argument("--adopt", action="store_true")
    a = ap.parse_args()
    if not L.has_plan():
        print("  move: no plan in this project (plan/plan.json)")
        return 2
    p = L.paths()
    d = L.load(p["root"])
    cfg, err = L.controller_config(d)
    if err:
        print("  move: %s" % err)
        return 2
    if a.adopt:
        if a.id:
            print("  move: --adopt takes no id")
            return 2
        import controller
        changes = [f["message"] for f in controller.one_writer_findings(p["root"], d, cfg or
                                                                        {"one_writer": True})]
        L.write_stamp(p["root"], d, "move.py --adopt")
        st = L.controller_state(p["root"])
        st.setdefault("adopted", []).append({"at": L.utc_now(), "changes": changes})
        L.atomic_write(L.controller_state_path(p["root"]),
                       __import__("json").dumps(st, indent=2, ensure_ascii=False) + "\n")
        print("  move: adopted the current state (%d change(s) accepted):" % len(changes))
        for c in changes:
            print("    - %s" % c)
        return 0
    if not a.id:
        print("  move: usage: move.py <id> --stage|--status|--task/--state|--to ... (or --adopt)")
        return 2
    if (a.task is None) != (a.state is None):
        print("  move: --task and --state go together")
        return 2
    if cfg and cfg["one_writer"]:
        import controller
        pending = controller.one_writer_findings(p["root"], d, cfg)
        if pending:
            # Restamping now would silently adopt every hand edit (review C1).
            print("  move: pending hand edits: revert them or run move.py --adopt; nothing written:")
            for f in pending:
                print("    - %s" % f["message"])
            return 1
    try:
        said, event = apply(d, a)
    except Usage as exc:
        print("  move: %s -- nothing written" % exc)
        return 2
    d["meta"]["updated"] = L.utc_now()
    L.save(d, p["root"])
    if cfg and cfg["one_writer"]:
        L.write_stamp(p["root"], d, "move.py " + " ".join(sys.argv[1:]))
    subprocess.run([sys.executable, os.path.join(HERE, "render.py")], capture_output=True)
    print("  move: %s" % said)
    if L.tracker_config(d, p["root"])[0]:
        print("  NEXT: run sync.py --tracker and reconcile the tracker")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`argparse` exits 2 on unknown flags, which matches the usage code. Replace the inline `__import__("json")` with a top-level `import json` when typing it in. The pending-edit check runs before argument errors on the id so a refused move never half-writes; `--adopt` runs before it (it is the remedy).

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m unittest tests/test_controller.py -v`
Expected: all OK.

- [ ] **Step 5: Commit**

```bash
git add plugins/plan-layer/scripts/move.py plugins/plan-layer/tests/test_controller.py
git commit -m "plan-layer: move.py, the one writer of stage, bucket, task state and release stage (S8)"
```

---

### Task 4: Relational expected rows (S3, lane B)

**Files:**
- Modify: `plugins/plan-layer/scripts/tracker.py` (`expected_rows`, `expected_hash`)
- Modify: `plugins/plan-layer/scripts/plan_lib.py` (`tracker_config`: read `relational`, `relations`, `task_status_map`, `release_status_map`, `relational_fetch`) — lane B touches only this function; lane A appends a new section, so they do not overlap
- Modify: `plugins/plan-layer/trackers/notion.json`, `generic.json`; `schema/plan.schema.json` (`meta.tracker.relational`, top-level `epics`)
- Test: `plugins/plan-layer/tests/test_relational.py` (create)

**Interfaces:**
- Produces:
  - `cfg["relational"]: bool`, `cfg["relations"]: {"epic": str, "story": str, "release": str}`, `cfg["task_status_map"]: {todo, active, blocked, done}`, `cfg["release_status_map"]: dict` (may be empty: the stage is shown as is)
  - In relational mode every expected row carries `"kind"` in `epic|story|task|release`; story rows carry `cfg["relations"]["epic"]` (the epic's name) and, when listed in a release, `cfg["relations"]["release"]`; task rows carry `cfg["relations"]["story"]` (the story's name).
  - `tracker.relational_faults(d) -> list[str]` (config FAILs: needs naming work-ids, story with an undeclared epic, story in two releases, task id under the wrong story)

- [ ] **Step 1: Capture the flat golden, then write the failing tests**

Before any change, from the worktree, record the 0.18.0 output of the `TrackerBase` fixture:

```bash
cd plugins/plan-layer && python3 - <<'EOF'
import json, sys, os
sys.path.insert(0, "tests"); sys.path.insert(0, "scripts")
import test_tracker as T, tracker, plan_lib as L, unittest
t = T.TrackerBase("run"); t.setUp(); t.write()
d = L.load(t.dir); cfg, _ = L.tracker_config(d, t.dir)
rows = tracker.expected_rows(d, cfg)
print(json.dumps({"rows": rows, "hash": tracker.expected_hash(rows, cfg)}, indent=1))
t.tearDown()
EOF
```

Paste the printed JSON into the test as `FLAT_GOLDEN` (literal, not recomputed).

```python
"""Relational tracker reconcile (0.19.0): epics, stories, tasks and releases with
their links, opt-in through meta.tracker.relational. Flat mode is unchanged."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_light_and_budget import Base, run  # noqa: E402
from test_tracker import TrackerBase, item  # noqa: E402
import plan_lib as L  # noqa: E402
import tracker  # noqa: E402

FLAT_GOLDEN = None  # replace with the literal captured in Step 1


class RelBase(TrackerBase):
    def setUp(self):
        super().setUp()
        self.d["meta"]["naming"] = "work-ids"
        self.d["meta"]["tracker"]["relational"] = True
        self.d["plans"]["now"][0]["tasks"] = [{"name": "E-01.S2.T1 form", "state": "active"},
                                              {"name": "untracked step", "state": "todo"}]
        self.d["epics"] = [{"id": "E-01", "name": "E-01 Accounts"}]
        self.d["releases"] = [{"id": "R-01", "name": "R-01 Accounts", "stage": "build",
                               "stories": ["E-01.S2"]}]

    def rows(self):
        self.write()
        d = L.load(self.dir)
        cfg, err = L.tracker_config(d, self.dir)
        self.assertIsNone(err)
        return {r["key"]: r for r in tracker.expected_rows(d, cfg)}


class TestFlatUnchanged(TrackerBase):
    def test_flat_rows_and_hash_byte_identical_to_0_18(self):
        self.write()
        d = L.load(self.dir)
        cfg, _ = L.tracker_config(d, self.dir)
        rows = tracker.expected_rows(d, cfg)
        self.assertEqual({"rows": rows, "hash": tracker.expected_hash(rows, cfg)}, FLAT_GOLDEN)


class TestRelationalRows(RelBase):
    def test_every_kind_with_its_links(self):
        r = self.rows()
        self.assertEqual(r["E-01"]["kind"], "epic")
        self.assertEqual(r["E-01"]["Name"], "E-01 Accounts")
        self.assertEqual(r["E-01"]["Status"], "In progress", "an epic with a story in now is building")
        self.assertEqual(r["E-01.S2"]["kind"], "story")
        self.assertEqual(r["E-01.S2"]["Epic"], "E-01 Accounts")
        self.assertEqual(r["E-01.S2"]["Release"], "R-01 Accounts")
        self.assertNotIn("Release", r["E-01.S3"])
        self.assertEqual(r["E-01.S2.T1"]["kind"], "task")
        self.assertEqual(r["E-01.S2.T1"]["Story"], "E-01.S2 Login page")
        self.assertEqual(r["E-01.S2.T1"]["Status"], "In progress")
        self.assertEqual(r["R-01"]["kind"], "release")
        self.assertEqual(r["R-01"]["Status"], "build", "no release_status_map: the stage as is")

    def test_task_without_a_task_id_is_not_mirrored_and_expected_says_so(self):
        self.write()
        out = run("tracker.py", "expected", project=self.dir)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        body = json.loads(out.stdout)
        self.assertNotIn("untracked step", json.dumps(body["rows"]))
        self.assertEqual(body["not_mirrored"], ["E-01.S2: untracked step"])

    def test_epic_status_done_when_every_story_is_finished(self):
        self.d["plans"]["now"], self.d["plans"]["next"] = [], []
        self.d["plans"]["done"] = [{"name": "E-01.S1 Signup", "period": "p", "outcome": "o"}]
        self.d["releases"][0]["stories"] = []
        self.assertEqual(self.rows()["E-01"]["Status"], "Done")

    def test_relational_hash_changes_with_a_link(self):
        self.write()
        d = L.load(self.dir)
        cfg, _ = L.tracker_config(d, self.dir)
        h1 = tracker.expected_hash(tracker.expected_rows(d, cfg), cfg)
        d["releases"][0]["stories"] = []
        self.assertNotEqual(h1, tracker.expected_hash(tracker.expected_rows(d, cfg), cfg))


class TestRelationalFaults(RelBase):
    def test_faults(self):
        cases = [
            (lambda d: d["meta"].pop("naming"), "work-ids"),
            (lambda d: d.__setitem__("epics", []), "E-01"),
            (lambda d: d["releases"].append({"id": "R-02", "name": "R-02 x", "stage": "build",
                                             "stories": ["E-01.S2"]}), "two releases"),
            (lambda d: d["plans"]["now"][0]["tasks"].append({"name": "E-01.S3.T1 x", "state": "todo"}),
             "E-01.S3.T1"),
        ]
        for mutate, word in cases:
            self.setUp()
            mutate(self.d)
            faults = tracker.relational_faults(self.d)
            self.assertTrue(any(word in f for f in faults), (word, faults))
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest tests/test_relational.py -v`
Expected: TestFlatUnchanged PASSES (golden matches the untouched code: that proves the golden is real); relational tests FAIL (`KeyError: 'kind'`, no `relational_faults`).

- [ ] **Step 3: Implement**

Adapters (`notion.json`, and the same keys in `generic.json` with neutral values):

```json
  "relations": {"epic": "Epic", "story": "Story", "release": "Release"},
  "task_status_map": {"todo": "Not started", "active": "In progress", "blocked": "Blocked", "done": "Done"},
  "release_status_map": {},
  "relational_fetch": "With the connector, query every row of each database the plan's meta.tracker.target names (one for epics, stories, tasks and releases, or one shared database; all pages). Save ONE JSON list; add \"kind\": \"epic\" | \"story\" | \"task\" | \"release\" to each row by the database it came from; flatten a relation to the related rows' titles joined by \", \"; every other property to a plain string as in fetch. Never build the list from the plan."
```

`plan_lib.tracker_config`: after the `rd` check, add

```python
    rel = t.get("relational", False)
    if not isinstance(rel, bool):
        return None, "meta.tracker.relational is %r — it must be true or false" % (rel,)
    relations = dict(adapter.get("relations") or {})
    if rel and not all(relations.get(k) for k in ("epic", "story", "release")):
        return None, "adapter %r has no relations {epic, story, release}; relational mode needs them" % kind
```

and return the extra keys `"relational": rel, "relations": relations, "task_status_map": dict(adapter.get("task_status_map") or {}), "release_status_map": dict(adapter.get("release_status_map") or {}), "fetch": adapter.get("relational_fetch") if rel else adapter.get("fetch", "")`. `target` may stay a string; a relational project that keeps several databases writes their ids in the one target string (out of scope to parse).

`tracker.py`: keep `expected_rows` as the flat path when `not cfg.get("relational")` (byte-identical) and add:

```python
def _story_rows(d, cfg):
    """The flat rows, each tagged kind=story with its epic and release links."""
    f, rel = cfg["fields"], cfg["relations"]
    epics = {e["id"]: e["name"] for e in d.get("epics") or [] if isinstance(e, dict)}
    in_release = {}
    for r in d.get("releases") or []:
        for s in r.get("stories") or []:
            in_release[s] = r["name"]
    rows = _flat_rows(d, cfg)
    for row in rows:
        row["kind"] = "story"
        epic = row["key"].split(".")[0]
        if epic in epics:
            row[rel["epic"]] = epics[epic]
        if row["key"] in in_release:
            row[rel["release"]] = in_release[row["key"]]
    return rows


def expected_rows(d, cfg):
    """(docstring as before, plus:) In relational mode, epics, stories, tasks and releases,
    each with "kind" and its links; tasks without a task id are listed by not_mirrored()."""
    if not cfg.get("relational"):
        return _flat_rows(d, cfg)
    f, rel, smap = cfg["fields"], cfg["relations"], cfg["status_map"]
    tmap = cfg["task_status_map"]
    stories = _story_rows(d, cfg)
    plans = d.get("plans") or {}
    rows = []
    for e in d.get("epics") or []:
        mine = [s for s in stories if s["key"].split(".")[0] == e["id"]]
        live = [s for s in mine if s[f["status"]] != smap["done"]]
        now_ids = {L.work_id(p.get("name")) for p in plans.get("now") or []}
        if mine and not live:
            status = smap["done"]
        elif any(s["key"] in now_ids for s in mine):
            status = smap["paused"] if L.paused_at(d) else smap.get("building", "building")
        else:
            status = smap.get("planned" if mine else "intent")
        rows.append({"key": e["id"], "kind": "epic", f["name"]: e["name"], f["status"]: status})
    rows += stories
    for bucket in ("now", "next"):
        for p in plans.get(bucket) or []:
            sid = L.work_id(p.get("name"))
            for t in p.get("tasks") or []:
                tid = L.work_id(t.get("name"))
                if tid and tid.rsplit(".T", 1)[0] == sid:
                    rows.append({"key": tid, "kind": "task", f["name"]: t["name"],
                                 f["status"]: tmap.get(t.get("state"), t.get("state")),
                                 rel["story"]: p["name"]})
    for r in d.get("releases") or []:
        row = {"key": r["id"], "kind": "release", f["name"]: r["name"],
               f["status"]: cfg["release_status_map"].get(r["stage"], r["stage"])}
        if f.get("stage"):
            row[f["stage"]] = r["stage"]
        rows.append(row)
    return rows


def not_mirrored(d):
    """Tasks of live items whose name carries no task id, as 'E-01.S2: name' (said, never silent)."""
    out = []
    for bucket in ("now", "next"):
        for p in (d.get("plans") or {}).get(bucket) or []:
            for t in p.get("tasks") or []:
                if not L.work_id(t.get("name")):
                    out.append("%s: %s" % (L.work_id(p.get("name")) or p.get("name"), t.get("name")))
    return out


def relational_faults(d):
    """Why a plan cannot be mirrored relationally, as FAIL strings; [] means it can."""
    out = []
    if (d.get("meta") or {}).get("naming") != "work-ids":
        out.append("meta.tracker.relational keys rows by work id — set meta.naming to \"work-ids\"")
    epics = {e.get("id") for e in d.get("epics") or [] if isinstance(e, dict)}
    seen = {}
    for r in d.get("releases") or []:
        for s in r.get("stories") or []:
            if s in seen:
                out.append("story %s is in two releases (%s, %s)" % (s, seen[s], r.get("id")))
            seen[s] = r.get("id")
    for bucket in ("now", "next"):
        for p in (d.get("plans") or {}).get(bucket) or []:
            sid = L.work_id(p.get("name"))
            if sid and sid.split(".")[0] not in epics:
                out.append("story %s: its epic %s is not declared in epics[]" % (sid, sid.split(".")[0]))
            for t in p.get("tasks") or []:
                tid = L.work_id(t.get("name"))
                if tid and tid.rsplit(".T", 1)[0] != sid:
                    out.append("task %s sits under %s; a task id names its own story" % (tid, sid))
    return out
```

Rename the current body of `expected_rows` to `_flat_rows` unchanged. In `main`'s `expected` branch, add `"not_mirrored": not_mirrored(d)` only when `cfg["relational"]` (flat output stays byte-identical). In `expected_hash`, when `cfg.get("relational")`, add `"kind"` and the three relation fields to the hashed columns; the flat branch is untouched. Schema: `meta.tracker.relational` (boolean) and top-level `epics` (array of `{id: "E-NN", name}`).

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m unittest tests/test_relational.py tests/test_tracker.py -v`
Expected: all OK (`test_tracker.py` unchanged and green proves flat compatibility twice).

- [ ] **Step 5: Commit**

```bash
git add plugins/plan-layer/scripts/tracker.py plugins/plan-layer/scripts/plan_lib.py plugins/plan-layer/trackers plugins/plan-layer/schema/plan.schema.json plugins/plan-layer/tests/test_relational.py
git commit -m "plan-layer: relational expected rows (epics, stories, tasks, releases with links), opt-in (S3)"
```

---

### Task 5: Relational diff and the reconcile record (S3, lane B)

**Files:**
- Modify: `plugins/plan-layer/scripts/tracker.py` (`read_actual`, `diff_rows`, `_known_names`, `reconcile`, `record`)
- Test: `plugins/plan-layer/tests/test_relational.py` (append)

**Interfaces:**
- Consumes: Task 4's `expected_rows`, `relational_faults`, `cfg["relations"]`.
- Produces: `tracker.diff_relational(expected, actual, cfg, root, d) -> list[str]`; `plan/tracker-state.json` gains `"actual_keys": [work ids or names of every actual row]` (used by Task 9); `reconcile` returns 2 with the fault text when `relational_faults(d)` is non-empty.

- [ ] **Step 1: Write the failing tests**

```python
class TestRelationalDiff(RelBase):
    def good(self):
        self.write()
        body = json.loads(run("tracker.py", "expected", project=self.dir).stdout)
        return [dict(r) for r in body["rows"]]

    def diff(self, rows):
        p = self.actual_file([{k: v for k, v in r.items() if k != "key"} for r in rows])
        return self.tracker("diff", "--actual", p)

    def test_clean_and_records_actual_keys(self):
        r = self.diff(self.good())
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("E-01.S2.T1", self.state()["actual_keys"])

    def test_missing_task_row_is_created_with_its_story_link(self):
        rows = [r for r in self.good() if r["key"] != "E-01.S2.T1"]
        r = self.diff(rows)
        self.assertEqual(r.returncode, 1)
        self.assertIn("create task row", r.stdout)
        self.assertIn("Story='E-01.S2 Login page'", r.stdout)

    def test_wrong_link_is_a_set_instruction(self):
        rows = self.good()
        for row in rows:
            if row["key"] == "E-01.S3":
                row["Release"] = "R-01 Accounts"
        r = self.diff(rows)
        self.assertEqual(r.returncode, 1)
        self.assertIn("set Release of 'E-01.S3 Logout page' to ''", r.stdout)

    def test_link_compared_on_work_id_so_a_retitled_epic_still_matches(self):
        rows = self.good()
        for row in rows:
            if row["key"] == "E-01.S2":
                row["Epic"] = "E-01 Accounts and sessions"
        self.assertEqual(self.diff(rows).returncode, 0)

    def test_same_id_under_another_kind_is_not_a_match(self):
        rows = self.good()
        for row in rows:
            if row["key"] == "R-01":
                row["kind"] = "story"
        r = self.diff(rows)
        self.assertEqual(r.returncode, 1)
        self.assertIn("create release row", r.stdout)

    def test_row_without_kind_is_unreadable_exit_2(self):
        rows = self.good()
        rows[0].pop("kind")
        r = self.diff(rows)
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("kind", r.stdout)

    def test_stray_epic_is_flagged(self):
        rows = self.good() + [{"kind": "epic", "Name": "E-07 Billing", "Status": "Planned"}]
        r = self.diff(rows)
        self.assertIn("row 'E-07 Billing' not in the plan", r.stdout)

    def test_plan_fault_exits_2_before_comparing(self):
        self.d["epics"] = []
        self.write()
        r = self.tracker("diff", "--actual", self.actual_file([]))
        self.assertEqual(r.returncode, 2)
        self.assertIn("not declared in epics", r.stdout)
        self.assertIsNone(self.state())
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest tests/test_relational.py -v`
Expected: the new tests FAIL (no `actual_keys`, rows compared flat, missing `kind` accepted).

- [ ] **Step 3: Implement**

`read_actual(path, cfg)`: replace the per-row loop with

```python
    nf = cfg["fields"]["name"]
    checked = list(cfg["fields"].values()) + (list(cfg["relations"].values()) if cfg.get("relational") else [])
    for i, r in enumerate(raw):
        if not isinstance(r, dict) or not isinstance(r.get(nf), str):
            return None, "row %d of %s is not an object with a %r text field" % (i, path, nf)
        if cfg.get("relational") and r.get("kind") not in KINDS:
            return None, ("row %d of %s has no kind (epic, story, task or release); tag each row by "
                          "the database it came from" % (i, path))
        for fname in checked:
            v = r.get(fname)
            if v is not None and not isinstance(v, str):
                return None, ("field %r of row %r is %s, not a plain string: flatten every "
                              "property to a plain string when fetching"
                              % (fname, r[nf], type(v).__name__))
    return raw, None
```

with `KINDS = ("epic", "story", "task", "release")` at module level.

`diff_rows`: signature `def diff_rows(expected, actual, cfg, known, relations=()):`; add the helper

```python
def _ids(value):
    """The work ids (else normalised titles) in a flattened link value 'E-01 A, E-02 B'."""
    return {L.work_id(x.strip()) or _norm(x) for x in str(value or "").split(",") if x.strip()}
```

replace the create branch with

```python
        if not hits:
            cols = [f["name"], f["status"], f.get("stage"), f.get("updated"), f.get("link")] + list(relations)
            kind = e.get("kind")
            out.append("create %srow: %s" % (kind + " " if kind else "",
                                             ", ".join("%s=%r" % (k, e[k]) for k in cols if k and k in e)))
            continue
```

(flat rows have no `kind`, so the flat text stays `create row: ...` and `test_tracker.py` is untouched), and replace the status/stage loop with

```python
        for k in ("status", "stage"):
            if f.get(k) and f[k] in e and L.nfc_text(r.get(f[k])) != L.nfc_text(e[f[k]]):
                out.append("set %s of '%s' to '%s'" % (f[k], shown, e[f[k]]))
        for rf in relations:
            if (rf in e or r.get(rf)) and _ids(r.get(rf)) != _ids(e.get(rf)):
                out.append("set %s of '%s' to '%s'" % (rf, shown, e.get(rf) or ""))
```

(`f[k] in e` changes nothing in flat mode: a flat row always carries status, and stage whenever the old code read it.)

Add

```python
def _task_ids(root, d):
    """Every task id the plan has held: tasks of now, next, done and the archive."""
    plans = d.get("plans") or {}
    adir = os.path.join(L.paths(root)["dir"], L.ARCHIVE_DIRNAME)
    items = list(plans.get("now") or []) + list(plans.get("next") or []) + list(plans.get("done") or [])
    for fn in ("done.json", "backlog.json"):
        try:
            items += json.load(open(os.path.join(adir, fn), encoding="utf-8")) or []
        except Exception:
            pass
    return {L.work_id(t.get("name")) for it in items if isinstance(it, dict)
            for t in (it.get("tasks") if isinstance(it.get("tasks"), list) else [])
            if isinstance(t, dict) and L.work_id(t.get("name"))}


def diff_relational(expected, actual, cfg, root, d):
    """Diff per kind (epic, story, task, release) with link comparison. Pure apart from reading the archive.

    A row matches only rows of its own kind, so R-01 tagged as a story is a
    stray story and a missing release. Returns instruction strings, kinds in order.
    """
    rels = list(cfg["relations"].values())
    epics = [e for e in d.get("epics") or [] if isinstance(e, dict)]
    releases = [r for r in d.get("releases") or [] if isinstance(r, dict)]
    known = {
        "epic": ({e.get("id") for e in epics}, {_norm(e.get("name")) for e in epics}, set(), set()),
        "story": _known_names(root, d),
        "task": (_task_ids(root, d), set(), set(), set()),
        "release": ({r.get("id") for r in releases}, {_norm(r.get("name")) for r in releases}, set(), set()),
    }
    out = []
    for k in KINDS:
        out += diff_rows([e for e in expected if e.get("kind") == k],
                         [r for r in actual if r.get("kind") == k], cfg, known[k], relations=rels)
    return out
```

`record`: signature `def record(root, d, cfg, drift, actual=None):`; build the dict as before and add, when `actual is not None`, `state["actual_keys"] = sorted({L.work_id(r[cfg["fields"]["name"]]) or _norm(r[cfg["fields"]["name"]]) for r in actual})` (flat reconciles gain the key too: a state file, not printed output).

`reconcile`: after `cfg` resolves and before reading the file:

```python
    if cfg.get("relational"):
        faults = relational_faults(d)
        if faults:
            for m in faults:
                print("  tracker: %s -- nothing was compared" % m)
            return 2
```

and replace the diff line with

```python
    todo = (diff_relational(exp, actual, cfg, p["root"], d) if cfg.get("relational")
            else diff_rows(exp, actual, cfg, known))
    record(p["root"], d, cfg, len(todo), actual)
```

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m unittest tests/test_relational.py tests/test_tracker.py -v`
Expected: all OK.

- [ ] **Step 5: Commit**

```bash
git add plugins/plan-layer/scripts/tracker.py plugins/plan-layer/tests/test_relational.py
git commit -m "plan-layer: relational diff per kind with links; the reconcile records actual keys (S3)"
```

---

### Task 6: Tracker drift is a red gate, fired by events (S3 + S7, one gate)

**Files:**
- Modify: `plugins/plan-layer/scripts/controller.py` (`tracker_findings`), `check.py` (remove its tracker block, lines 717-734 at base, by moving it), `gate_hook.py`, `brief.py`, `sync.py`, `pause.py` (pass the event)
- Test: `plugins/plan-layer/tests/test_controller.py` (append)

**Interfaces:**
- Consumes: Task 2's `findings`, Task 5's `relational_faults`.
- Produces: `controller.tracker_findings(root, d, level) -> list`; `controller.EVENTS = ("stop", "session-start", "sync", "pause")` plus `stage:<id>` and `release:<stage>`; the event each caller passes: Stop hook `stop`, SessionStart `session-start`, `sync.py` `sync`, `pause.py` `pause`, `move.py` `stage:<id>` / `release:<stage>` (Task 7).

- [ ] **Step 1: Write the failing tests**

```python
def stop_hook(project, session=None):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=project)
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "gate_hook.py")], cwd=project, env=env,
                       input=json.dumps({"session_id": session or uuid.uuid4().hex}),
                       capture_output=True, text=True)
    return json.loads(r.stdout) if r.stdout.strip() else {}


class TestTrackerRedGate(ControllerBase):
    def setUp(self):
        super().setUp()
        self.d["meta"]["tracker"] = {"kind": "notion", "target": "db-1"}
        stamp_now(self)

    def test_without_controller_tracker_signals_stay_drift(self):
        del self.d["meta"]["controller"]
        self.write()
        _, fails, drifts = self.gate()
        self.assertFalse([f for f in fails if "tracker mirror" in f], fails)
        self.assertTrue([m for m in drifts if "never reconciled" in m], drifts)

    def test_with_controller_never_reconciled_fails(self):
        _, fails, _ = self.gate()
        self.assertTrue([f for f in fails if "never reconciled" in f], fails)

    def test_stop_hook_blocks_with_the_reconcile_step(self):
        run("render.py", project=self.dir)
        out = stop_hook(self.dir)
        self.assertEqual(out.get("decision"), "block", out)
        self.assertIn("tracker.py diff --actual", out["reason"])

    def test_reconciled_clean_then_a_move_reddens_it_again(self):
        exp = json.loads(run("tracker.py", "expected", project=self.dir).stdout)["rows"]
        p = os.path.join(self.dir, "actual.json")
        json.dump([{k: v for k, v in r.items() if k != "key"} for r in exp], open(p, "w"))
        self.assertEqual(run("tracker.py", "diff", "--actual", p, project=self.dir).returncode, 0)
        _, fails, _ = self.gate()
        self.assertFalse([f for f in fails if "tracker mirror" in f], fails)
        self.assertEqual(self.move("E-01.S2", "--stage", "verified").returncode, 0)
        _, fails, _ = self.gate()
        self.assertTrue([f for f in fails if "tracker mirror" in f and "differ" in f], fails)

    def test_relational_fault_is_a_gate_fail(self):
        self.d["meta"]["tracker"]["relational"] = True
        self.d["epics"] = []
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in fails if "not declared in epics" in f], fails)

    def test_tracker_message_text_is_unchanged_from_0_18(self):
        del self.d["meta"]["controller"]
        self.write()
        _, _, drifts = self.gate()
        self.assertIn("tracker mirror (notion) was never reconciled — fetch its rows and run "
                      "tracker.py diff --actual <file>", drifts)

    def test_callers_pass_their_event(self):
        for script, event in (("gate_hook.py", '"stop"'), ("brief.py", '"session-start"'),
                              ("sync.py", '"sync"'), ("pause.py", '"pause"')):
            self.assertIn(event, open(os.path.join(SCRIPTS, script)).read(), script)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest tests/test_controller.py -v`
Expected: the controller-on tests FAIL (signals are DRIFT; Stop hook does not block); `test_callers_pass_their_event` FAILs.

- [ ] **Step 3: Implement**

Move (cut, not copy) the tracker block from `check.run` into `controller.py`, text unchanged:

```python
import tracker  # noqa: E402

EVENTS = ("stop", "session-start", "sync", "pause")


def tracker_findings(root, d, level):
    """The tracker mirror's state as findings: malformed config FAILs always; a
    mirror never reconciled, reconciled against other expected rows, or left with
    differences is `level` (FAIL when meta.controller is set: drift is a red gate;
    DRIFT otherwise, as in 0.18.0). Messages are the 0.18.0 text."""
    tcfg, terr = L.tracker_config(d, root)
    if terr:
        return [_f("tracker", terr)]
    if not tcfg:
        return []
    if tcfg.get("relational"):
        faults = tracker.relational_faults(d)
        if faults:
            return [_f("tracker", m) for m in faults]
    st = L.tracker_state(root)
    if not st or not st.get("at"):
        return [_f("tracker", "tracker mirror (%s) was never reconciled — fetch its rows and run "
                   "tracker.py diff --actual <file>" % tcfg["kind"], level)]
    if st.get("expected_hash") != tracker.expected_hash(tracker.expected_rows(d, tcfg), tcfg):
        return [_f("tracker", "tracker mirror (%s): the rows the plan now expects differ from those last "
                   "reconciled (%s) — fetch the rows and reconcile again" % (tcfg["kind"], st["at"]), level)]
    if st.get("drift"):
        return [_f("tracker", "tracker mirror (%s): the last reconcile (%s) left %s difference(s) — "
                   "apply them and diff again" % (tcfg["kind"], st["at"], st["drift"]), level)]
    return []
```

`findings` becomes:

```python
def findings(root, d, event=None):
    cfg, err = L.controller_config(d)
    out = [_f("config", err)] if err else one_writer_findings(root, d, cfg)
    out += tracker_findings(root, d, "FAIL" if (cfg or err) else "DRIFT")
    return out
```

`check.py` drops its own tracker block and the `import tracker` (now unused there). Callers: `gate_hook.py` `check.run(event="stop")`; `brief.py` `session_start` `check.run(event="session-start")` (pre-compact keeps no event); `sync.py` runs `[sys.executable, check.py, "--event", "sync"]` for the gate leg; `pause.py` `check.run(root, event="pause")`.

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m unittest tests/test_controller.py tests/test_tracker.py tests/test_pause.py -v`
Expected: all OK (the 0.18.0 tracker gate tests pass unchanged because without `meta.controller` the level stays DRIFT).

- [ ] **Step 5: Commit**

```bash
git add plugins/plan-layer/scripts plugins/plan-layer/tests/test_controller.py
git commit -m "plan-layer: tracker drift is a red gate under meta.controller; every caller fires its event (S3, S7)"
```

---

### Task 7: Declared rules on events; a failing rule refuses the move (S7)

**Files:**
- Modify: `plugins/plan-layer/scripts/controller.py` (`rule_faults`, `changed_files`, `rule_findings`), `move.py` (run the event's rules before writing), schema (`meta.controller.rules[]`)
- Test: `plugins/plan-layer/tests/test_controller.py` (append)

**Interfaces:**
- Consumes: Task 6's `EVENTS`, Task 3's `move.event_for`.
- Produces:
  - Rule shape `{"name": str, "on": [event...], "if_changed": [glob...], "then_changed": [glob...], "why": str}` (all required; `kind` is implied `co_change`, the only kind)
  - `controller.rule_faults(rules, stage_ids) -> list[str]`
  - `controller.changed_files(root, base) -> (set[str] | None, str | None)` (committed since the merge-base with `base`, plus uncommitted and untracked)
  - `controller.rule_findings(root, cfg, event) -> list` (only rules whose `on` holds `event`; FAIL). Callers: `findings` and `move.py` (a stage move, and each stage change `--adopt` accepts: review I5)
  - `controller.stage_events(stamp_writes, d) -> list[str]` (the `stage:`/`release:` events implied by every stage that differs from the stamp)

- [ ] **Step 1: Write the failing tests**

```python
def git(cwd, *a):
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t"] + list(a),
                   cwd=cwd, check=True, capture_output=True)


RULE = {"name": "changelog with code", "on": ["stage:verified"], "if_changed": ["src/*.py"],
        "then_changed": ["CHANGELOG.md"], "why": "a missed changelog entry was caught by hand twice"}


class TestRules(ControllerBase):
    def setUp(self):
        super().setUp()
        self.d["meta"]["controller"]["rules"] = [dict(RULE)]
        git(self.dir, "checkout", "-q", "-b", "main")
        os.makedirs(os.path.join(self.dir, "src"))
        open(os.path.join(self.dir, "src", "app.py"), "w").write("x = 1\n")
        open(os.path.join(self.dir, "CHANGELOG.md"), "w").write("# log\n")
        stamp_now(self)
        run("render.py", project=self.dir)
        git(self.dir, "add", "-A")
        git(self.dir, "commit", "-q", "-m", "base")
        git(self.dir, "checkout", "-q", "-b", "feature")
        open(os.path.join(self.dir, "src", "app.py"), "a").write("y = 2\n")
        git(self.dir, "commit", "-q", "-am", "feature work")  # merge-base must sit behind HEAD

    def test_rule_fires_only_on_its_event(self):
        _, fails, _ = self.gate()
        self.assertFalse([f for f in fails if "changelog with code" in f], fails)
        r = run("check.py", "--json", "--event", "stage:verified", project=self.dir)
        out = json.loads(r.stdout)
        hit = [f for f in out["fails"] if "changelog with code" in f]
        self.assertTrue(hit, out["fails"])
        self.assertIn("CHANGELOG.md", hit[0])
        self.assertIn("src/app.py", hit[0])

    def test_failing_rule_refuses_the_move_and_writes_nothing(self):
        before = open(os.path.join(self.dir, "plan", "plan.json")).read()
        r = self.move("E-01.S2", "--stage", "verified")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("changelog with code", r.stdout)
        self.assertEqual(open(os.path.join(self.dir, "plan", "plan.json")).read(), before)

    def test_satisfied_rule_lets_the_move_through(self):
        open(os.path.join(self.dir, "CHANGELOG.md"), "a").write("- y\n")
        self.assertEqual(self.move("E-01.S2", "--stage", "verified").returncode, 0)

    def test_unmeasurable_base_fails_loudly_never_passes(self):
        self.d = self.read()
        self.d["meta"]["controller"]["base"] = "no-such-branch"
        self.write()
        L.write_stamp(self.dir, self.d, "test")
        r = self.move("E-01.S2", "--stage", "verified")
        self.assertEqual(r.returncode, 1)
        self.assertIn("cannot measure", r.stdout)

    def test_base_at_head_measures_nothing_and_fails(self):
        git(self.dir, "checkout", "-q", "main")
        r = self.move("E-01.S2", "--stage", "verified")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("behind HEAD", r.stdout)

    def test_adopt_runs_the_rules_of_each_stage_it_accepts(self):
        self.d = self.read()
        self.d["plans"]["now"][0]["stage"] = "verified"
        self.write()
        before = self.stamp()
        r = self.move("--adopt")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("changelog with code", r.stdout)
        self.assertEqual(self.stamp(), before, "a refused adopt stamps nothing")
        open(os.path.join(self.dir, "CHANGELOG.md"), "a").write("- y\n")
        self.assertEqual(self.move("--adopt").returncode, 0)

    def test_rule_shape_faults(self):
        import controller
        stages = ["intent", "verified"]
        self.assertEqual(controller.rule_faults([dict(RULE)], stages), [])
        for bad, word in (({"on": ["lunch"]}, "lunch"), ({"on": ["stage:flying"]}, "flying"),
                          ({"why": ""}, "why"), ({"then_changed": []}, "then_changed"),
                          ({"extra": 1}, "extra")):
            rule = dict(RULE, **bad)
            faults = controller.rule_faults([rule], stages)
            self.assertTrue(any(word in f for f in faults), (bad, faults))

    def test_bad_rule_is_a_gate_fail_on_any_event(self):
        self.d = self.read()
        self.d["meta"]["controller"]["rules"] = [dict(RULE, on=["lunch"])]
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in fails if "lunch" in f], fails)

    def test_release_event(self):
        self.d = self.read()
        self.d["releases"] = [{"id": "R-01", "name": "R-01 x", "stage": "build", "stories": []}]
        self.d["meta"]["controller"]["rules"] = [dict(RULE, on=["release:production"])]
        self.write()
        L.write_stamp(self.dir, self.d, "test")
        self.assertEqual(self.move("R-01", "--stage", "production").returncode, 1)
        self.assertEqual(self.move("R-01", "--stage", "gate").returncode, 0)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest tests/test_controller.py -v`
Expected: TestRules FAIL (no rule evaluation, no refusal).

- [ ] **Step 3: Implement in `controller.py`, then `move.py`**

```python
import fnmatch

_RULE_KEYS = ("name", "on", "if_changed", "then_changed", "why")


def rule_faults(rules, stage_ids):
    """Malformed rules as FAIL strings. A rule is a co-change rule: when any path
    matching if_changed changed since the base, some path matching each
    then_changed pattern must have changed too. Events: stop, session-start, sync,
    pause, stage:<cycle stage id>, release:<stage>."""
    out = []
    for i, r in enumerate(rules):
        where = "meta.controller.rules[%d]" % i
        if not isinstance(r, dict):
            out.append("%s is not an object" % where)
            continue
        where = "rule %r" % r.get("name", i)
        for k in sorted(set(r) - set(_RULE_KEYS)):
            out.append("%s has unknown key %r (known: %s)" % (where, k, ", ".join(_RULE_KEYS)))
        for k in ("name", "why"):
            if not (isinstance(r.get(k), str) and r[k].strip()):
                out.append("%s needs %s (text)" % (where, k))
        for k in ("on", "if_changed", "then_changed"):
            v = r.get(k)
            if not (isinstance(v, list) and v and all(isinstance(x, str) and x for x in v)):
                out.append("%s needs %s (a non-empty list of text)" % (where, k))
        for e in r.get("on") or []:
            if not isinstance(e, str):
                continue
            ok = (e in EVENTS or (e.startswith("stage:") and e[6:] in stage_ids)
                  or (e.startswith("release:") and e[8:].strip()))
            if not ok:
                out.append("%s: event %r is not one of %s, stage:<%s>, release:<stage>"
                           % (where, e, ", ".join(EVENTS), "|".join(stage_ids)))
    return out


def changed_files(root, base):
    """Paths changed since the merge-base with `base`, plus uncommitted and untracked.

    Returns (set, None) or (None, reason). A missing base is a reason, never an
    empty set: a rule that measured nothing must not pass.
    """
    mb = L.git(root, "merge-base", base, "HEAD")
    if not mb:
        return None, "cannot measure changes: no merge-base between %r and HEAD" % base
    if mb == L.git(root, "rev-parse", "HEAD"):
        # On the base itself nothing committed is measured (review I2).
        return None, ("cannot measure changes: the merge-base with %r is HEAD itself — set "
                      "meta.controller.base to a ref behind HEAD" % base)
    files = set(L.git(root, "diff", "--name-only", mb).splitlines())
    files |= set(L.git(root, "ls-files", "--others", "--exclude-standard").splitlines())
    return {f for f in files if f}, None


def stage_events(writes, d):
    """Events implied by every stage in the plan that differs from the stamp's (for --adopt)."""
    cur = L.controlled(d)
    old_i, old_r = (writes or {}).get("items") or {}, (writes or {}).get("releases") or {}
    ev = ["stage:%s" % v["stage"] for k, v in sorted(cur["items"].items())
          if (old_i.get(k) or {}).get("stage") != v["stage"]]
    ev += ["release:%s" % s for k, s in sorted(cur["releases"].items()) if old_r.get(k) != s]
    return sorted(set(ev))


def rule_findings(root, cfg, event):
    """FAIL for each rule bound to `event` whose co-change does not hold."""
    if not cfg or not event:
        return []
    mine = [r for r in cfg["rules"] if event in (r.get("on") or [])]
    if not mine:
        return []
    files, why = changed_files(root, cfg["base"])
    if why:
        return [_f("rule", "rule %r on %s: %s" % (r["name"], event, why)) for r in mine]
    out = []
    for r in mine:
        hit = sorted(f for f in files if any(fnmatch.fnmatch(f, p) for p in r["if_changed"]))
        if not hit:
            continue
        missing = [p for p in r["then_changed"] if not any(fnmatch.fnmatch(f, p) for f in files)]
        if missing:
            out.append(_f("rule", "rule %r on %s: %s changed but nothing matching %s did (%s)"
                          % (r["name"], event, ", ".join(hit[:3]) + (", …" if len(hit) > 3 else ""),
                             ", ".join(missing), r["why"])))
    return out
```

`findings` adds, after the config read: when `cfg`, `out += [_f("config", m) for m in rule_faults(cfg["rules"], stage_ids(d))]`, and only if those are empty, `out += rule_findings(root, cfg, event)`. `stage_ids(d)` = `[s["id"] for s in (d.get("cycle") or L.DEFAULT_CYCLE)["stages"]]`.

`move.py` main, after `said, event = apply(d, a)` and before saving:

```python
    if event and cfg:
        import controller
        blocked = [f["message"] for f in controller.rule_findings(p["root"], cfg, event)]
        if blocked:
            print("  move: refused -- the %s rules fail; nothing written:" % event)
            for m in blocked:
                print("    - %s" % m)
            return 1
```

`move.py --adopt` (review I5), before `L.write_stamp`: an adopt accepts stage changes, so it fires their events too.

```python
        if cfg:
            prior = (L.controller_state(p["root"]) or {}).get("writes")
            blocked = [f["message"] for ev in controller.stage_events(prior, d)
                       for f in controller.rule_findings(p["root"], cfg, ev)]
            if blocked:
                print("  move: --adopt refused -- rules on the stages it would accept fail; nothing stamped:")
                for m in blocked:
                    print("    - %s" % m)
                return 1
```

Schema: `meta.controller.rules` items `{name, on, if_changed, then_changed, why}`, all required, `additionalProperties: false`.

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m unittest tests/test_controller.py -v`
Expected: all OK.

- [ ] **Step 5: Commit**

```bash
git add plugins/plan-layer/scripts/controller.py plugins/plan-layer/scripts/move.py plugins/plan-layer/schema/plan.schema.json plugins/plan-layer/tests/test_controller.py
git commit -m "plan-layer: co-change rules bound to events; a failing rule refuses the stage move (S7)"
```

---

### Task 8: The handoff reads the controller's diff (S4)

**Files:**
- Modify: `plugins/plan-layer/scripts/pause.py` (`render_handoff`, `pause`)
- Test: `plugins/plan-layer/tests/test_pause.py` (append)

**Interfaces:**
- Consumes: `summary["controller"]` from the one `check.run(root, event="pause")` call pause already makes (review M5: no second diff), `L.controller_config`, `L.controller_state`.
- Produces: HANDOFF.md sections, only when `meta.controller` is set: `## Reconcile (the controller's diff at <time>)`, `## Git per active item`, `## Decisions since the last handoff`; `controller-state.json` gains `"handoff": {"at", "head"}`; `render_handoff(d, git_line, read_at, fails, drifts, extra=None)` (extra = list of lines appended before `## Traps`).

- [ ] **Step 1: Write the failing tests**

```python
def git(cwd, *a):
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t"] + list(a),
                   cwd=cwd, check=True, capture_output=True)


class TestHandoffReconcile(PauseBase):
    def setUp(self):
        super().setUp()
        self.d["meta"]["naming"] = "work-ids"
        self.d["meta"]["controller"] = {"one_writer": False, "decision_log": "docs/decisions.md"}
        self.d["meta"]["tracker"] = {"kind": "notion", "target": "db-1"}
        os.makedirs(os.path.join(self.dir, "docs"))
        open(os.path.join(self.dir, "docs", "decisions.md"), "w").write("# Decisions\n")
        self.write()
        git(self.dir, "checkout", "-q", "-b", "main")
        git(self.dir, "add", "-A")
        git(self.dir, "commit", "-q", "-m", "base")
        git(self.dir, "checkout", "-q", "-b", "e-01-login")

    def test_without_controller_the_note_is_as_before(self):
        self.d["meta"].pop("controller")
        self.write()
        self.pause()
        self.assertNotIn("## Reconcile", self.handoff())

    def test_reconcile_section_lists_the_open_diff(self):
        r = self.pause()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        h = self.handoff()
        self.assertIn("## Reconcile", h)
        self.assertIn("never reconciled", h)
        self.assertIn("CONTROLLER:", r.stdout)

    def test_git_per_active_item_names_branch_and_last_commit(self):
        open(os.path.join(self.dir, "x.txt"), "w").write("x")
        git(self.dir, "add", "x.txt")
        git(self.dir, "commit", "-q", "-m", "E-01.S2: wire the form")
        self.pause()
        h = self.handoff()
        self.assertIn("## Git per active item", h)
        self.assertIn("e-01-login", h)
        self.assertIn("E-01.S2: wire the form", h)

    def test_decisions_added_since_the_last_handoff(self):
        self.pause()
        with open(os.path.join(self.dir, "docs", "decisions.md"), "a") as fh:
            fh.write("- D-001 sessions expire after a day\n- D-002 no remember-me box\n")
        git(self.dir, "add", "-A")
        git(self.dir, "commit", "-q", "-m", "decisions")
        self.pause()
        h = self.handoff()
        self.assertIn("## Decisions since the last handoff", h)
        self.assertIn("D-001", h)
        self.assertIn("D-002", h)
        self.assertIn("transcript", h)

    def test_handoff_head_is_recorded(self):
        self.pause()
        st = json.load(open(os.path.join(self.dir, "plan", "controller-state.json")))
        self.assertEqual(len(st["handoff"]["head"]), 40)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest tests/test_pause.py -v`
Expected: the new tests FAIL (no sections, no record); the existing pause tests pass.

- [ ] **Step 3: Implement in `pause.py`**

```python
import re

DECISION_ID = re.compile(r"\bD-[0-9]{3,}\b")


def git_per_item(root, d):
    """For each active work id (plans.now): branches whose name holds its epic slug, and
    the last commit whose message names the id. Read now, never recalled."""
    out = []
    branches = L.git(root, "branch", "--list", "--format=%(refname:short)").splitlines()
    for p in (d.get("plans") or {}).get("now") or []:
        wid = L.work_id(p.get("name"))
        if not wid:
            continue
        slug = wid.split(".")[0].lower()
        mine = [b for b in branches if slug in b.lower()] or ["no branch names %s" % slug]
        last = L.git(root, "log", "-1", "--format=%h %s", "--fixed-strings", "--grep=" + wid)
        out.append("- %s: branches %s; last commit naming it: %s"
                   % (wid, ", ".join(mine), last or "none"))
    return out or ["- nothing active"]


def decisions_since(root, cfg, since_head):
    """Decision ids on lines added to the decision log since the last handoff's HEAD
    (else since the merge-base with the base branch)."""
    log = cfg.get("decision_log")
    if not log:
        return ["- no decision log configured (meta.controller.decision_log)"]
    since = since_head or L.git(root, "merge-base", cfg["base"], "HEAD")
    if not since:
        return ["- cannot measure: no earlier handoff and no merge-base with %r" % cfg["base"]]
    added = [ln[1:] for ln in L.git(root, "diff", since, "--", log).splitlines()
             if ln.startswith("+") and not ln.startswith("+++")]
    ids = sorted({m for ln in added for m in DECISION_ID.findall(ln)})
    return ["- added to %s since %s: %s" % (log, since[:7], ", ".join(ids) or "none")]
```

In `pause(p)`: read `cfg, _ = L.controller_config(d)` and `head = L.git(root, "rev-parse", "HEAD")` before the save; change `fails, drifts, _ = check.run(root)` to `fails, drifts, summary = check.run(root, event="pause")`; then, when `cfg`:

```python
        found = summary.get("controller") or []
        prev = ((L.controller_state(root) or {}).get("handoff") or {}).get("head")
        extra = ["## Reconcile (the controller's diff at %s)" % at, ""]
        extra += ["- [%s] %s: %s" % (f["level"], f["check"], f["message"]) for f in found] \
            or ["- clean: nothing to reconcile"]
        extra += ["", "## Git per active item", ""] + git_per_item(root, d)
        extra += ["", "## Decisions since the last handoff", ""] + decisions_since(root, cfg, prev)
        extra += ["- Agent step: search this session's transcript for decisions given in passing "
                  "and append each to the decision log before ending.", ""]
        st = L.controller_state(root) or {}
        st["handoff"] = {"at": at, "head": head}
        L.atomic_write(L.controller_state_path(root), json.dumps(st, indent=2) + "\n")
        for f in found:
            print("  CONTROLLER: [%s] %s" % (f["level"], f["message"]))
```

Pass `extra` into `render_handoff`, which inserts it just before `## Traps`. Pause still exits 0 (ruling 4: a handoff is never blocked).

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m unittest tests/test_pause.py -v`
Expected: all OK.

- [ ] **Step 5: Commit**

```bash
git add plugins/plan-layer/scripts/pause.py plugins/plan-layer/tests/test_pause.py
git commit -m "plan-layer: the handoff reads the controller's diff, git per item and decisions since the last handoff (S4)"
```

---

### Task 9: Inventory parity (S9)

**Files:**
- Modify: `plugins/plan-layer/scripts/controller.py` (`extract`, `inventory_findings`), schema (top-level `inventory`)
- Test: `plugins/plan-layer/tests/test_inventory.py` (create)

**Interfaces:**
- Consumes: `findings`, Task 5's `tracker-state.json` `actual_keys`.
- Produces: top-level `inventory: {<name>: {"items": [str] | "from": {"file", "json"?}, "covered_by": [{"list", "file", "json"?} | {"list", "tracker": true}], "exempt": [{"item", "list", "why"}]}}`; `controller.extract(root, src) -> (list[str] | None, str | None)`; `controller.inventory_findings(root, d) -> list` (FAIL). Checked whenever `inventory` is present, with or without `meta.controller`.

- [ ] **Step 1: Write the failing tests**

```python
"""Inventory parity (0.19.0): a declared inventory against every list that must cover it."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_light_and_budget import Base, SCRIPTS  # noqa: E402

AGENTS = ["agent-%02d" % i for i in range(1, 11)]


def inv(msgs):
    return [m for m in msgs if m.startswith("inventory ")]


class InvBase(Base):
    def put(self, rel, text):
        path = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").write(text)

    def setUp(self):
        super().setUp()
        self.put("ops/backup.sh", "for a in agent-01 agent-02 agent-03 agent-04 agent-05; do b $a; done\n")
        self.put("ops/copy.json", json.dumps({"jobs": [{"host": "host-a"}]}))
        self.d["inventory"] = {
            "agents": {"items": AGENTS, "covered_by": [{"list": "nightly backup", "file": "ops/backup.sh"}]},
            "hosts": {"items": ["host-a", "host-b"],
                      "covered_by": [{"list": "copy job", "file": "ops/copy.json", "json": "jobs[].host"}]},
        }


class TestParity(InvBase):
    def test_absent_inventory_is_silent(self):
        del self.d["inventory"]
        self.write()
        _, fails, drifts = self.gate()
        self.assertEqual(inv(fails + drifts), [])

    def test_backup_listing_five_of_ten_fails_naming_the_five(self):
        self.write()
        rc, fails, _ = self.gate()
        self.assertEqual(rc, 1)
        hit = [f for f in inv(fails) if "nightly backup" in f]
        self.assertEqual(len(hit), 1, fails)
        self.assertIn("5 of 10", hit[0])
        for a in AGENTS[5:]:
            self.assertIn(a, hit[0])

    def test_copy_job_covering_one_host_of_two_fails(self):
        self.write()
        _, fails, _ = self.gate()
        hit = [f for f in inv(fails) if "copy job" in f]
        self.assertTrue(hit and "host-b" in hit[0] and "1 of 2" in hit[0], fails)

    def test_full_coverage_is_clean_and_word_match_is_whole_word(self):
        self.put("ops/backup.sh", " ".join(AGENTS) + "\n")
        self.put("ops/copy.json", json.dumps({"jobs": [{"host": "host-a"}, {"host": "host-b"}]}))
        self.write()
        _, fails, _ = self.gate()
        self.assertEqual(inv(fails), [], fails)
        self.put("ops/backup.sh", " ".join(AGENTS[1:]).replace("agent-10", "agent-100") + " agent-010\n")
        self.write()
        _, fails, _ = self.gate()
        hit = inv(fails)[0]
        self.assertIn("agent-01", hit)
        self.assertIn("agent-10", hit)

    def test_exempt_needs_a_why(self):
        self.d["inventory"]["hosts"]["exempt"] = [{"item": "host-b", "list": "copy job", "why": "retiring"}]
        self.write()
        _, fails, _ = self.gate()
        self.assertFalse([f for f in inv(fails) if "copy job" in f], fails)
        self.d["inventory"]["hosts"]["exempt"] = [{"item": "host-b", "list": "copy job"}]
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "why" in f], fails)

    def test_unreadable_list_fails_loudly(self):
        self.d["inventory"]["hosts"]["covered_by"][0]["file"] = "ops/missing.json"
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "ops/missing.json" in f and "cannot read" in f], fails)

    def test_a_path_that_extracts_nothing_fails_never_passes(self):
        self.d["inventory"]["hosts"]["covered_by"][0]["json"] = "jobs[].hostname"
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "extracted nothing" in f], fails)

    def test_inventory_read_from_a_file(self):
        self.put("ops/agents.json", json.dumps({"agents": [{"name": a} for a in AGENTS]}))
        self.d["inventory"]["agents"]["items"] = None
        del self.d["inventory"]["agents"]["items"]
        self.d["inventory"]["agents"]["from"] = {"file": "ops/agents.json", "json": "agents[].name"}
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "5 of 10" in f], fails)

    def test_tracker_rows_as_a_covering_list(self):
        self.d["inventory"] = {"agents": {"items": ["agent-01", "agent-02"],
                                          "covered_by": [{"list": "tracker rows", "tracker": True}]}}
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "never reconciled" in f], fails)
        json.dump({"at": "2026-01-01T00:00:00Z", "actual_keys": ["agent-01"]},
                  open(os.path.join(self.dir, "plan", "tracker-state.json"), "w"))
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "agent-02" in f], fails)

    def test_malformed_inventory_fails(self):
        self.d["inventory"] = {"agents": {"items": AGENTS}}
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "covered_by" in f], fails)

    def test_a_bare_path_as_covering_list_fails_and_the_stop_hook_still_blocks(self):
        import subprocess, uuid
        self.d["inventory"]["hosts"]["covered_by"] = ["ops/copy.json"]
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "must be an object" in f], fails)
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.dir)
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "gate_hook.py")], cwd=self.dir,
                           env=env, input=json.dumps({"session_id": uuid.uuid4().hex}),
                           capture_output=True, text=True)
        self.assertEqual(json.loads(r.stdout).get("decision"), "block", r.stdout + r.stderr)

    def test_from_needs_a_json_path(self):
        del self.d["inventory"]["agents"]["items"]
        self.d["inventory"]["agents"]["from"] = {"file": "ops/backup.sh"}
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "from needs" in f], fails)

    def test_sentence_full_stop_after_a_name_still_counts(self):
        self.put("ops/backup.sh", "# covers " + ", ".join(AGENTS) + ".\n")
        self.write()
        _, fails, _ = self.gate()
        self.assertFalse([f for f in inv(fails) if "nightly backup" in f], fails)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest tests/test_inventory.py -v`
Expected: every non-silent test FAILs (no inventory check).

- [ ] **Step 3: Implement in `controller.py`**

```python
import json
import re


def _walk(obj, path):
    """Values at a dot path where 'a[]' steps into each element and 'a{}' takes keys."""
    vals = [obj]
    for part in [p for p in path.split(".") if p]:
        nxt = []
        name, each, keys = part.rstrip("[]{}"), part.endswith("[]"), part.endswith("{}")
        for v in vals:
            v = v.get(name) if (isinstance(v, dict) and name) else v
            if each and isinstance(v, list):
                nxt.extend(v)
            elif keys and isinstance(v, dict):
                nxt.extend(v.keys())
            elif v is not None and not (each or keys):
                nxt.append(v)
        vals = nxt
    return [str(v) for v in vals if isinstance(v, (str, int))]


def extract(root, src):
    """The entries of one list. src = {"file", "json"?}. Returns (entries, None) or (None, reason).

    With "json": the values at that path. Without: the file's text, kept whole
    (coverage is then a whole-word match). An unreadable file or an empty
    extraction is a reason, never an empty list.
    """
    path = os.path.join(root, src.get("file") or "")
    try:
        text = open(path, encoding="utf-8").read()
    except Exception as exc:
        return None, "cannot read %s (%s)" % (src.get("file"), exc.__class__.__name__)
    if not src.get("json"):
        return [text], None
    try:
        vals = _walk(json.loads(text), src["json"])
    except Exception as exc:
        return None, "cannot parse %s as JSON (%s)" % (src["file"], exc)
    if not vals:
        return None, "%s at %r extracted nothing — the path or the file is wrong" % (src["file"], src["json"])
    return vals, None


def _covered(item, entries, whole_text):
    if whole_text:
        # A trailing full stop ends a sentence, not a name: "agent-10." covers agent-10, "agent-10.b" does not.
        return re.search(r"(?<![\w.-])%s(?![\w-]|\.\w)" % re.escape(item), entries[0]) is not None
    return item in entries


def inventory_findings(root, d):
    """FAIL for every inventory item missing from a list that must cover it, and for
    any list that cannot be read. Exemptions need a why."""
    out = []
    inv = d.get("inventory")
    if inv is None:
        return out
    if not isinstance(inv, dict):
        return [_f("inventory", "inventory is %r — an object of named inventories" % (inv,))]
    for name, spec in sorted(inv.items()):
        who = "inventory %r" % name
        if not (isinstance(spec, dict) and isinstance(spec.get("covered_by"), list) and spec["covered_by"]):
            out.append(_f("inventory", "%s needs covered_by: a non-empty list of lists to check" % who))
            continue
        if "from" in spec:
            src = spec["from"]
            if not (isinstance(src, dict) and src.get("file") and src.get("json")):
                out.append(_f("inventory", "%s: from needs {file, json}: the inventory is a list of names "
                              "read at a JSON path" % who))
                continue
            items, why = extract(root, src)
            if why:
                out.append(_f("inventory", "%s: %s" % (who, why)))
                continue
        else:
            items = spec.get("items")
        if not (isinstance(items, list) and items and all(isinstance(i, str) and i for i in items)):
            out.append(_f("inventory", "%s needs items (a non-empty list of names) or from" % who))
            continue
        exempt = {}
        for e in spec.get("exempt") or []:
            if not (isinstance(e, dict) and e.get("item") and e.get("list") and (e.get("why") or "").strip()):
                out.append(_f("inventory", "%s: an exemption needs item, list and why: %r" % (who, e)))
                continue
            exempt.setdefault(e["list"], set()).add(e["item"])
        for cov in spec["covered_by"]:
            if not isinstance(cov, dict):
                out.append(_f("inventory", "%s: each covered_by entry must be an object {list, file, json?} "
                              "or {list, tracker: true}, not %r" % (who, cov)))
                continue
            label = cov.get("list") or cov.get("file") or "list"
            if cov.get("tracker"):
                st = L.tracker_state(root)
                if not st or "actual_keys" not in st:
                    out.append(_f("inventory", "%s, list %r: the tracker was never reconciled with "
                                  "keys recorded — run the tracker reconcile" % (who, label)))
                    continue
                entries, whole = [str(k).casefold() for k in st["actual_keys"]], False
                check = [i.casefold() for i in items]
            else:
                entries, why = extract(root, cov)
                if why:
                    out.append(_f("inventory", "%s, list %r: %s" % (who, label, why)))
                    continue
                whole, check = not cov.get("json"), items
            missing = [orig for orig, i in zip(items, check)
                       if orig not in exempt.get(label, set()) and not _covered(i, entries, whole)]
            if missing:
                out.append(_f("inventory", "%s: list %r covers %d of %d — missing %s"
                              % (who, label, len(items) - len(missing), len(items), ", ".join(missing))))
    return out
```

`findings` appends `inventory_findings(root, d)` last. The `inventory` key's messages all start with `inventory ` so tests filter on it. Schema: top-level `inventory` as described in Interfaces.

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m unittest tests/test_inventory.py -v`
Expected: all OK.

- [ ] **Step 5: Commit**

```bash
git add plugins/plan-layer/scripts/controller.py plugins/plan-layer/schema/plan.schema.json plugins/plan-layer/tests/test_inventory.py
git commit -m "plan-layer: inventory parity: a declared inventory against every list that must cover it (S9)"
```

---

### Task 10: Docs, writer-matrix table, version 0.19.0, engineering-method pointers

**Files:**
- Modify: `plugins/plan-layer/skills/plan-layer/SKILL.md` (new "Controller" section; commands table gains `/plan-layer move`; the writer matrix as a table between `<!-- writer-matrix -->` and `<!-- /writer-matrix -->`; "What the gate checks" lists the new FAILs; `description` mentions `move`)
- Modify: `plugins/plan-layer/README.md` (section "Tracker mirror, and pause" becomes "Controller: one writer, tracker, rules, inventory, handoff")
- Modify: `plugins/plan-layer/trackers/README.md` (relational mode, `kind`, relations, `relational_fetch`)
- Modify: `plugins/plan-layer/CHANGELOG.md`, `plugins/plan-layer/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` (0.19.0)
- Modify (**rebase after 0.4.0**): `plugins/engineering-method/skills/engineering-method/SKILL.md` §2 principle 15, `plugins/engineering-method/skills/engineering-method/references/docs-and-decisions.md`
- Test: `plugins/plan-layer/tests/test_controller.py` (append)

- [ ] **Step 1: Write the failing tests**

```python
class TestDocs(unittest.TestCase):
    def test_skill_writer_table_equals_the_code(self):
        import re
        text = open(os.path.join(PLUGIN, "skills", "plan-layer", "SKILL.md"), encoding="utf-8").read()
        block = re.search(r"<!-- writer-matrix -->(.*?)<!-- /writer-matrix -->", text, re.S)
        self.assertTrue(block, "SKILL.md has no writer-matrix block")
        rows = [[c.strip().strip("`") for c in ln.strip().strip("|").split("|")]
                for ln in block.group(1).splitlines()
                if ln.startswith("|") and not re.match(r"^\|\s*(Field|-)", ln)]
        self.assertEqual(rows, [[w["field"], w["writer"], w["enforced"]] for w in L.WRITERS])

    def test_version_is_0_19_0_with_a_changelog_entry(self):
        pl = json.load(open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json")))
        self.assertEqual(pl["version"], "0.19.0")
        self.assertTrue(open(os.path.join(PLUGIN, "CHANGELOG.md")).read().startswith(
            "# Changelog\n\n## 0.19.0"))

    def test_no_private_names_in_the_new_files(self):
        """Generic examples only; the scan list itself is kept outside the repo."""
        for rel in ("scripts/controller.py", "scripts/move.py", "tests/test_controller.py",
                    "tests/test_relational.py", "tests/test_inventory.py"):
            text = open(os.path.join(PLUGIN, rel), encoding="utf-8").read()
            self.assertNotRegex(text, r"https?://(www\.)?notion\.so/", rel)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest tests/test_controller.py -v`
Expected: TestDocs FAILs (no block, version 0.18.0).

- [ ] **Step 3: Write the docs**

SKILL.md "Controller (opt-in)" section, in this order, each a short paragraph: the pattern (declared state, observed state, one diff, drift is a red gate, the agent is never the trigger); `meta.controller` keys; `move.py` commands and that hand edits FAIL, with `--adopt` used only on the human's say-so; the writer-matrix table (columns `Field | Writer | Enforced`, rows exactly `L.WRITERS`); events and who fires each; rules (one kind, co-change; example `{"name": "changelog with code", "on": ["stage:verified"], "if_changed": ["src/*.py"], "then_changed": ["CHANGELOG.md"], "why": "…"}`; `fnmatch` `*` also matches `/`); relational tracker; inventory (example with `agent-01`… and `ops/backup.sh`, whole-word match, exemptions need a why); handoff sections. Keep the SKILL.md additions under 500 words.

Two worked rule examples, configuration only (no new mechanism; the Warp study's ideas checked against Task 7):
- **An approval recorded before live-tier work proceeds:** `{"name": "approval before production", "on": ["release:production"], "if_changed": ["deploy/*"], "then_changed": ["docs/approvals/*.md"], "why": "live changes need a recorded approval"}`. Say plainly what it proves: that an approval file changed on the branch, not who wrote it; the content stays a human check.
- The second idea (an invariant with a runnable check) is **not** expressible as a co-change rule (rules match paths, they run nothing); see Out of scope.

CHANGELOG `## 0.19.0 — <date measured at commit>`: one paragraph per story (S8, S3, S7, S4, S9), the opt-in and compatibility statement, and `Tests: N new; M passed, 0 skipped (base 246)` with N and M read from the controller's full-suite run in Task 11 (fill at that step, never estimated). Both manifests to `0.19.0`.

engineering-method, shipped as **engineering-method 0.4.1** (rebase after 0.4.0; a one-line CHANGELOG entry; word-neutral in SKILL.md):
- SKILL.md principle 15: replace `reconciled at every progress report (plan-layer: \`/plan-layer sync --tracker\`;` with `reconciled on events by plan-layer's controller (\`move.py\`, \`sync --tracker\`;` and confirm the body word count is unchanged or lower (`python3 -m unittest tests/test_skill_budget.py`).
- docs-and-decisions.md, after the sentence ending "not another line in the instructions file (SKILL.md principle 7)." (line 95 at base): add one sentence: "With plan-layer, a "changed X, so Y must change" rule is a co-change rule in `meta.controller.rules`, fired on a stage event."

- [ ] **Step 4: Run to verify**

Run: `python3 -m unittest tests/test_controller.py tests/test_plan_layer.py -v` and, for engineering-method, `python3 -m unittest discover -s plugins/engineering-method/tests` from the repo root.
Expected: all OK (the manifest test confirms the two versions agree).

- [ ] **Step 5: Commit**

```bash
git add plugins/plan-layer plugins/engineering-method .claude-plugin/marketplace.json
git commit -m "plan-layer 0.19.0: controller docs, writer-matrix table, changelog; engineering-method pointers (rebase after 0.4.0)"
```

---

### Task 11: Full suite, whole-branch review, scan

- [ ] **Step 1: Full suites, exit code kept**

```bash
set -o pipefail
cd plugins/plan-layer && python3 -m unittest tests/*.py 2>&1 | tail -4
cd ../.. && python3 -m unittest discover -s plugins/engineering-method/tests 2>&1 | tail -3
```
Expected: `OK` on both; plan-layer count = 246 + the new tests, 0 skipped. Write the measured numbers into the CHANGELOG `Tests:` line; amend nothing, commit it as its own commit.

- [ ] **Step 2: Prove the reds are possible on the real scripts**

In a scratch copy of the fixture plan: hand-edit a stage (gate exits 1), remove an agent from a backup file (gate exits 1), leave the tracker unreconciled with `meta.controller` (Stop hook prints `"decision": "block"`), then fix each and see exit 0. Paste the outputs into the review brief.

- [ ] **Step 3: Whole-branch review (Fable 5.2, fresh agent, own worktree)**

Brief: the intent paragraph from this plan, the Fit section, the diff `git diff 5982357...tracker-controller` (split if over ~60 KB), and these probes to write and run, not reason about: (a) can any path change a controlled field without the gate failing (edit by hand, `roll`, `pause`, `--adopt`)? (b) is flat-mode tracker output byte-identical to 0.18.0? (c) can a rule pass without measuring (missing base, detached HEAD, shallow clone)? (d) can an inventory check pass on an unreadable or empty list? (e) does the Stop hook still never trap a session (same failures twice, internal error)? (f) fit check: is anything built twice (gate, hook, diff), and is each piece tied to S8, S3, S7, S4 or S9? The reviewer reports its model id; an unreproduced finding is labelled a hypothesis.

- [ ] **Step 4: Fix rounds**

Opus fixes Criticals and Importants red-first; a scoped Fable re-review only for a Critical or an Important on the gate seam; test-only rounds are read by the controller from the diff.

- [ ] **Step 5: Identifier scan and final commit**

Run the local identifier scan (its list lives outside the repo) over `git diff 5982357...HEAD`; expect zero hits. Do not push.

---

## Review rulings (Fable 5.2, 25 Nov 2026), adopted

1. `move.py --adopt` stays (first opt-in, after a git merge); it now fires the rules of each stage change it accepts (I5) and every other move refuses while hand edits are pending (C1).
2. The one writer covers stage, bucket, task state and release stage. Prose status is dropped from the stamp (`tracker.expected_rows` never reads it); `--status` stays as a convenience.
3. Drift is red by default once `meta.controller` is set; no switch.
4. `pause.py` exits 0; the note and `CONTROLLER:` lines carry the diff.
5. Both new scripts stay (`controller.py` library, `move.py` CLI).

Review fixes folded in: C1 (Task 3), I1 (Task 2), I2 and I5 (Task 7), I3 (Tasks 2 and 9), I4 (Tasks 1 and 2), M1 (Lanes), M2 (Task 2), M3 (Task 3), M4 (Task 9), M5 (Task 8), M6 (Tasks 5 and 7), M7 (Task 10).
