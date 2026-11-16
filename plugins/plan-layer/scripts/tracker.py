#!/usr/bin/env python3
"""Mirror plan state into an external tracker by reconciling, not by trusting.

  tracker.py expected                    # the rows the tracker SHOULD hold, as JSON
  tracker.py diff --actual <file.json>   # compare with the rows the agent fetched

plan-layer cannot call a tracker's API; the agent does, through that tracker's
connector. This script is the other half of a GitOps-style reconcile loop:
derive EXPECTED from the plan (the source of truth), compare to ACTUAL, print
every difference as an exact instruction in the adapter's own terms, and record
that the comparison happened. The adapter (trackers/<kind>.json) is data, so a
new tracker is one new file. meta.tracker in plan.json turns the feature on.

Exit codes for `diff`: 0 clean, 1 drift found, 2 unreadable input or no tracker
configured. Unparseable input is never treated as clean: a green result that
compared nothing is the dangerous kind.

The reconcile is recorded in plan/tracker-state.json (time, drift count, the
plan `updated` it was compared against) so the gate can say when it is stale.
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_lib as L  # noqa: E402


def _norm(text):
    """Case-folded, whitespace-collapsed text, for matching a title across trackers."""
    return " ".join(str(text or "").split()).casefold()


def _title(name):
    """The item name without its leading work id ('Login page' from 'E-01.S2 Login page')."""
    wid = L.work_id(name)
    if not wid:
        return name
    return name[len(wid):].lstrip(" \t:·,;-")


def expected_rows(d, cfg):
    """The rows the tracker should hold, derived from the plan alone.

    Covers plans.now, plans.next and the last cfg['recent_done'] items of
    plans.done (done is oldest-first, so the tail is the most recent; older
    done work lives in plan/archive and is not mirrored). Status comes from the
    adapter: the stage's mapped value, "Paused" for active items while
    meta.paused is set, "Done" for finished items. Inputs: plan dict, config
    from plan_lib.tracker_config. Output: list of dicts keyed by "key" (the work
    id, else the name) plus the adapter's field names. No side effects.
    """
    f, smap = cfg["fields"], cfg["status_map"]
    updated = (d.get("meta") or {}).get("updated")
    paused = L.paused_at(d) is not None
    plans = d.get("plans") or {}
    done = plans.get("done") or []
    recent = done[-cfg["recent_done"]:] if cfg["recent_done"] else []
    rows = []
    for bucket, items in (("now", plans.get("now") or []), ("next", plans.get("next") or []),
                          ("done", recent)):
        for it in items:
            name = it.get("name")
            if bucket == "done":
                stage, status = "recorded", smap["done"]
            else:
                stage = it.get("stage")
                status = smap["paused"] if (paused and bucket == "now") else smap.get(stage, stage)
            row = {"key": L.work_id(name) or name, f["name"]: name, f["status"]: status,
                   f["stage"]: stage, f["updated"]: updated}
            link = it.get("link") or it.get("plan_file")
            if link:
                row[f["link"]] = link
            rows.append(row)
    return rows


def _known_names(root, d):
    """Every id and normalised name the plan has ever held: live items and archived history.

    Why: a tracker row for work that has rolled out of plan.json is history, not
    a stray, so it must not be reported as 'not in the plan'.
    """
    items = []
    plans = d.get("plans") or {}
    for b in ("now", "next", "done"):
        items.extend(plans.get(b) or [])
    adir = os.path.join(L.paths(root)["dir"], L.ARCHIVE_DIRNAME)
    for fn in ("done.json", "backlog.json"):
        try:
            items.extend(json.load(open(os.path.join(adir, fn), encoding="utf-8")))
        except Exception:
            pass
    ids, names = set(), set()
    for it in items:
        if isinstance(it, dict) and isinstance(it.get("name"), str):
            wid = L.work_id(it["name"])
            if wid:
                ids.add(wid)
            names.add(_norm(it["name"]))
            names.add(_norm(_title(it["name"])))
    return ids, names


def read_actual(path, cfg):
    """Load the rows the agent fetched. Returns (rows, error); one is None.

    Accepts a JSON list of objects, or an object with a "rows" list (what
    `expected` prints). Every row must be an object whose name field is a
    string. Anything else is an error, never an empty result.
    """
    try:
        raw = json.load(open(path, encoding="utf-8"))
    except Exception as exc:
        return None, "cannot read %s: %s" % (path, exc)
    if isinstance(raw, dict) and isinstance(raw.get("rows"), list):
        raw = raw["rows"]
    if not isinstance(raw, list):
        return None, "%s must hold a JSON list of row objects" % path
    nf = cfg["fields"]["name"]
    for i, r in enumerate(raw):
        if not isinstance(r, dict) or not isinstance(r.get(nf), str):
            return None, "row %d of %s is not an object with a %r text field" % (i, path, nf)
    return raw, None


def diff_rows(expected, actual, cfg, known_ids, known_names):
    """Compare expected with actual rows. Returns a list of instruction strings; [] means clean.

    Rows are matched on the work id at the start of the name; a row lacking the
    id but matching the item's title is matched too and reported as a rename.
    Name, Status and Stage are compared; Updated and Link are not. Pure.
    """
    f = cfg["fields"]
    by_id, no_id = {}, []
    for r in actual:
        wid = L.work_id(r[f["name"]])
        if wid:
            by_id.setdefault(wid, []).append(r)
        else:
            no_id.append(r)
    used, out = [], []
    for e in expected:
        wid = L.work_id(e[f["name"]])
        if wid:
            hits = list(by_id.get(wid, []))
            renamed = False
            if not hits:
                t = _norm(_title(e[f["name"]]))
                hits = [r for r in no_id if _norm(r[f["name"]]) == t and r not in used]
                renamed = bool(hits)
        else:
            hits = [r for r in actual if _norm(r[f["name"]]) == _norm(e[f["name"]])]
            renamed = False
        if not hits:
            fields = ", ".join("%s=%r" % (k, e[k]) for k in
                               [f["name"], f["status"], f["stage"], f["updated"], f["link"]] if k in e)
            out.append("create row: %s" % fields)
            continue
        used.extend(hits)
        if len(hits) > 1:
            out.append("duplicate rows for %r (%d found): archive all but one"
                       % (e["key"], len(hits)))
        r = hits[0]
        shown = r[f["name"]]
        if renamed:
            out.append("rename '%s' to start with its work id: '%s'" % (shown, e[f["name"]]))
        for k in ("status", "stage"):
            if r.get(f[k]) != e[f[k]]:
                out.append("set %s of '%s' to '%s'" % (f[k], shown, e[f[k]]))
    for r in actual:
        if any(r is u for u in used):
            continue
        nm = r[f["name"]]
        wid = L.work_id(nm)
        if (wid and wid in known_ids) or _norm(nm) in known_names or _norm(_title(nm)) in known_names:
            continue
        out.append("row '%s' not in the plan: archive or add to the plan" % nm)
    return out


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record(root, d, cfg, drift):
    """Write plan/tracker-state.json: when, how much drift, which plan `updated` it was compared to."""
    L.atomic_write(L.tracker_state_path(root), json.dumps(
        {"at": _now(), "drift": drift, "plan_updated": (d.get("meta") or {}).get("updated"),
         "kind": cfg["kind"]}, indent=2) + "\n")


def reconcile(actual_path, quiet=False):
    """Run one reconcile against a fetched file. Prints the instructions; returns the exit code.

    Side effect: records the reconcile in plan/tracker-state.json when the
    input was readable (clean or drifting). Unreadable input records nothing.
    """
    p = L.paths()
    d = L.load(p["root"])
    cfg, err = L.tracker_config(d)
    if err or cfg is None:
        print("  tracker: %s" % (err or "meta.tracker is not set in plan.json"))
        return 2
    actual, err = read_actual(actual_path, cfg)
    if err:
        print("  tracker: %s -- nothing was compared" % err)
        return 2
    exp = expected_rows(d, cfg)
    ids, names = _known_names(p["root"], d)
    todo = diff_rows(exp, actual, cfg, ids, names)
    record(p["root"], d, cfg, len(todo))
    if todo:
        print("  tracker: %d difference(s) from the plan; carry out each, then fetch the rows and diff again:"
              % len(todo))
        for t in todo:
            print("    - %s" % t)
        return 1
    print("  tracker: OK -- %d expected row(s) match %s" % (len(exp), cfg["kind"]))
    return 0


def next_step(d, cfg):
    """Print the expected-rows summary and the exact next step for the agent. Returns 0."""
    exp = expected_rows(d, cfg)
    f = cfg["fields"]
    print("  tracker: %s %s -- %d expected row(s):" % (cfg["kind"], cfg["target"], len(exp)))
    for r in exp:
        print("    - %s | %s | %s" % (r[f["name"]], r[f["status"]], r[f["stage"]]))
    print("  next: fetch the rows -- %s" % cfg["fetch"])
    print("        save them to a file, then run: sync.py --tracker --actual <file>")
    return 0


def main():
    if not L.has_plan():
        return 0
    args = sys.argv[1:]
    cmd = args[0] if args else ""
    d = L.load()
    cfg, err = L.tracker_config(d)
    if err or cfg is None:
        print("  tracker: %s" % (err or "meta.tracker is not set in plan.json"))
        return 2
    if cmd == "expected":
        print(json.dumps({"tracker": cfg["kind"], "target": cfg["target"],
                          "plan_updated": (d.get("meta") or {}).get("updated"),
                          "fetch": cfg["fetch"], "rows": expected_rows(d, cfg)},
                         indent=2, ensure_ascii=False))
        return 0
    if cmd == "diff":
        if "--actual" not in args or args.index("--actual") + 1 >= len(args):
            print("  tracker: diff needs --actual <file.json> (rows fetched from the tracker)")
            return 2
        return reconcile(args[args.index("--actual") + 1])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
