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
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_lib as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TASK_STATES = ("done", "active", "todo", "blocked")
STAMP_UNREADABLE = ("  move: stamp unreadable: delete plan/controller-state.json and run move.py --adopt "
                    "(review the plan first: adopt accepts its current state)")


class Usage(Exception):
    """A request move.py will not write; the message says why (exit 2)."""


def event_for(kind, stage):
    """The event a move fires: stage:<id> for an item, release:<stage> for a release."""
    return ("release:%s" if kind == "release" else "stage:%s") % stage


def duplicates(d):
    """Duplicate work ids and duplicate task names, as words naming each. Pure."""
    import controller
    return (["work id %s" % w for w in L.duplicate_ids(d)]
            + ["task name %r of %s" % (t, w) for w, t in controller.duplicate_tasks(d)])


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
        dups = duplicates(d)
        if dups:
            print("  move: --adopt refused -- rename the duplicate(s) %s first; nothing stamped"
                  % "; ".join(dups))
            return 1
        try:
            if not isinstance((L.controller_state(p["root"]) or {}).get("writes"), dict):
                changes = ["first stamp of the current state"]
            else:
                changes = [f["message"] for f in controller.one_writer_findings(
                    p["root"], d, cfg or {"one_writer": True})]
        except Exception:
            print(STAMP_UNREADABLE)
            return 2
        # (Task 7 inserts the rule check for the accepted stage changes here.)
        L.write_stamp(p["root"], d, "move.py --adopt")
        st = L.controller_state(p["root"])
        st.setdefault("adopted", []).append({"at": L.utc_now(), "changes": changes})
        L.atomic_write(L.controller_state_path(p["root"]),
                       json.dumps(st, indent=2, ensure_ascii=False) + "\n")
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
        try:
            pending = controller.one_writer_findings(p["root"], d, cfg)
        except Exception:
            print(STAMP_UNREADABLE)
            return 2
        if pending:
            # Restamping now would silently adopt every hand edit (review C1).
            if duplicates(d):
                print("  move: refused -- rename the duplicate(s) %s first; nothing written:"
                      % "; ".join(duplicates(d)))
            else:
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
