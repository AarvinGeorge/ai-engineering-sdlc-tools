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
import tracker  # noqa: E402

EVENTS = ("stop", "session-start", "sync", "pause")  # plus stage:<id> and release:<stage>


_MISSING = object()  # a task absent from a record, distinct from a task with no state (None)


def _f(check, message, level="FAIL"):
    return {"check": check, "level": level, "message": message}


def first_stage(d):
    """The cycle's first stage id ('intent' by default): where a new idea enters."""
    stages = (d.get("cycle") or L.DEFAULT_CYCLE).get("stages") or [{}]
    return stages[0].get("id")


def duplicate_tasks(d):
    """(work id, task name) pairs where one live item lists the same task name twice. Pure.

    controlled() keys tasks by name, so a repeat would hide a state change.
    """
    out = []
    for bucket in ("now", "next"):
        for it in (d.get("plans") or {}).get(bucket) or []:
            wid = L.work_id(it.get("name")) if isinstance(it, dict) else None
            names = [str(t.get("name")) for t in it.get("tasks") or [] if isinstance(t, dict)] if wid else []
            out += [(wid, n) for n in sorted({n for n in names if names.count(n) > 1})]
    return out


FIX = "revert the hand edit, or run move.py --adopt (with the owner's say-so)"  # the one remedy a hand edit has (review N2: move.py refuses while edits are pending)


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
    dups = [_f("one_writer", "%s is the work id of more than one live item or release — rename the "
               "duplicate to its own id (--adopt cannot clear this)" % w) for w in L.duplicate_ids(d)]
    dups += [_f("one_writer", "task name %r appears more than once in %s — rename the duplicate "
                "(--adopt cannot clear this)" % (t, w)) for w, t in duplicate_tasks(d)]
    if not isinstance(rec, dict):
        return dups + [_f("one_writer", "meta.controller.one_writer is on but move.py has recorded no write — "
                          "run move.py --adopt once to stamp the current state")]
    if dups:
        return dups
    cur, first = L.controlled(d), first_stage(d)
    archived = L.archived_ids(root)
    out = []
    ritems, citems = rec.get("items") or {}, cur["items"]
    for wid in sorted(set(ritems) | set(citems)):
        a, b = ritems.get(wid), citems.get(wid)
        if a and b:
            if a["bucket"] != b["bucket"]:
                out.append(_f("one_writer", "%s moved from plans.%s to plans.%s by hand — %s"
                              % (wid, a["bucket"], b["bucket"], FIX)))
            if a["stage"] != b["stage"]:
                out.append(_f("one_writer", "stage of %s is %r but move.py last wrote %r — changed by hand; %s"
                              % (wid, b["stage"], a["stage"], FIX)))
            for t in sorted(set(a["tasks"]) | set(b["tasks"])):
                ta, tb = a["tasks"].get(t, _MISSING), b["tasks"].get(t, _MISSING)
                if ta is _MISSING and tb != "todo":
                    out.append(_f("one_writer", "task %r of %s entered at %r by hand — %s"
                                  % (t, wid, tb, FIX)))
                elif tb is _MISSING and ta not in (_MISSING, "todo"):
                    out.append(_f("one_writer", "task %r of %s (%s) was removed by hand — %s" % (t, wid, ta, FIX)))
                elif ta is not _MISSING and tb is not _MISSING and ta != tb:
                    out.append(_f("one_writer", "task %r of %s is %r but move.py last wrote %r — changed by "
                                  "hand; %s" % (t, wid, tb, ta, FIX)))
        elif b:
            if not (b["bucket"] == "next" and b["stage"] == first
                    and all(s == "todo" for s in b["tasks"].values())):
                out.append(_f("one_writer", "%s entered plans.%s at stage %r by hand — %s (an item enters "
                              "plans.next at %r, then moves with move.py)" % (wid, b["bucket"], b["stage"], FIX, first)))
        elif wid not in archived and not (a["bucket"] == "next" and a["stage"] == first):
            out.append(_f("one_writer", "%s left plans.%s by hand (it was at %r) — %s (finish work with "
                          "move.py %s --to done --outcome \"<text>\")" % (wid, a["bucket"], a["stage"], FIX, wid)))
    rrel = rec.get("releases") or {}
    for rid in sorted(set(rrel) | set(cur["releases"])):
        if rid not in rrel:
            out.append(_f("one_writer", "release %s (stage %r) was added by hand — %s"
                          % (rid, cur["releases"][rid], FIX)))
        elif rid not in cur["releases"]:
            out.append(_f("one_writer", "release %s (stage %r) was removed by hand — %s"
                          % (rid, rrel[rid], FIX)))
        elif rrel[rid] != cur["releases"][rid]:
            out.append(_f("one_writer", "stage of %s is %r but move.py last wrote %r — changed by hand; %s"
                          % (rid, cur["releases"][rid], rrel[rid], FIX)))
    return out


def tracker_findings(root, d, level):
    """The tracker mirror's state as findings.

    What: malformed config always FAILs; a mirror never reconciled, reconciled
    against other expected rows, or left with differences is `level`.
    Use when: the gate, the handoff and the hooks need the mirror's state.
    Inputs: root, plan dict, level ("FAIL" when meta.controller is set, so drift
    is a red gate; "DRIFT" otherwise, as in 0.18.0). Output: list of findings,
    messages are the 0.18.0 text. Side effects: none (reads the reconcile record).
    Role: gate check.
    """
    tcfg, terr = L.tracker_config(d, root)
    if terr:
        return [_f("tracker", terr)]
    if not tcfg:
        return []
    if tcfg.get("relational"):
        faults = tracker.relational_faults(d, root)
        if faults:
            return [_f("tracker", m, level) for m in faults]
    st = L.tracker_state(root)
    if not st or not st.get("at"):
        return [_f("tracker", "tracker mirror (%s) was never reconciled — fetch its rows and run "
                   "tracker.py diff --actual <file>" % tcfg["kind"], level)]
    if st.get("expected_hash") != tracker.expected_hash(tracker.expected_rows(d, tcfg, root), tcfg):
        return [_f("tracker", "tracker mirror (%s): the rows the plan now expects differ from those last "
                   "reconciled (%s) — fetch the rows and reconcile again" % (tcfg["kind"], st["at"]), level)]
    if st.get("drift"):
        return [_f("tracker", "tracker mirror (%s): the last reconcile (%s) left %s difference(s) — "
                   "apply them and diff again" % (tcfg["kind"], st["at"], st["drift"]), level)]
    return []


def findings(root, d, event=None):
    """The whole diff, in check order. Inputs: root, plan dict, event name or None. Pure reads."""
    cfg, err = L.controller_config(d)
    out = [_f("config", err)] if err else one_writer_findings(root, d, cfg)
    out += tracker_findings(root, d, "FAIL" if (cfg or err) else "DRIFT")
    return out
