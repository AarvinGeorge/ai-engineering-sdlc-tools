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
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_lib as L  # noqa: E402


_SEPARATORS = " \t:\u00b7,;-\u2014\u2013"


def _norm(text):
    """Unicode-normalised, case-folded, whitespace-collapsed text, for matching titles across trackers."""
    return L.nfc_text(str(text or "")).casefold()


def _title(name):
    """The item name without its leading work id and the separators after it.

    'E-01.S2 \u2014 Login page' and 'E-01.S2: Login page' both give 'Login page'; a
    name with no work id is returned unchanged.
    """
    wid = L.work_id(name)
    if not wid:
        return name
    return name[len(wid):].lstrip(_SEPARATORS)


def _optional(cfg, key):
    """The tracker's name for an optional field, or None when the adapter does not declare it."""
    return cfg["fields"].get(key)


def _flat_rows(d, cfg):
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
            row = {"key": L.work_id(name) or name, f["name"]: name, f["status"]: status}
            for key, value in (("stage", stage), ("updated", updated),
                               ("link", it.get("link") or it.get("plan_file"))):
                if f.get(key) and value:
                    row[f[key]] = value
            rows.append(row)
    return rows


def _epics(d):
    """The well-formed epics: dicts with a string id and name. Malformed ones are faults, never rows."""
    return [e for e in d.get("epics") or []
            if isinstance(e, dict) and isinstance(e.get("id"), str) and isinstance(e.get("name"), str)]


def _releases(d):
    """The well-formed releases: string id, name and stage, a list (or absent) stories."""
    return [r for r in d.get("releases") or []
            if isinstance(r, dict) and all(isinstance(r.get(k), str) for k in ("id", "name", "stage"))
            and isinstance(r.get("stories") or [], list)]


def _task_of(sid, tid):
    """True when tid is a task id of story sid (E-01.S2 -> E-01.S2.T<n>)."""
    return bool(sid and tid and re.fullmatch(re.escape(sid) + r"\.T[0-9]+", tid))


def _story_rows(d, cfg):
    """The flat rows, each tagged kind=story with its epic and release links.

    Why: relational mode needs each story to name its epic and release. Inputs:
    plan dict, config. Output: list of row dicts. Side effects: none.
    """
    rel = cfg["relations"]
    epics = {e["id"]: e["name"] for e in _epics(d)}
    in_release = {}
    for r in _releases(d):
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


def expected_rows(d, cfg, root=None):
    """The rows the tracker should hold, derived from the plan alone.

    Flat mode (the default) is the 0.18 mirror, unchanged. In relational mode:
    epics, stories, tasks and releases, each with "kind" and its links; a task
    is mirrored only when its id is <its story id>.T<n> (others are listed by
    not_mirrored()). An epic's status comes from all the work the plan has held
    (plans.done plus the archive when root is given), not from mirrored rows.
    Inputs: plan dict, config, optional project root. Output: list of row dicts
    keyed by "key". No side effects.
    """
    if not cfg.get("relational"):
        return _flat_rows(d, cfg)
    f, rel, smap = cfg["fields"], cfg["relations"], cfg["status_map"]
    tmap = cfg["task_status_map"]
    stories = _story_rows(d, cfg)
    plans = d.get("plans") or {}
    known_ids, _n, done_ids, _dn = _known_names(root, d)
    now_ids = {L.work_id(p.get("name")) for p in plans.get("now") or []}
    rows = []
    for e in _epics(d):
        mine = {i for i in known_ids if re.fullmatch(re.escape(e["id"]) + r"\.S[0-9]+", i)}
        if mine and mine <= done_ids:
            status = smap["done"]
        elif mine & now_ids:
            status = smap["paused"] if L.paused_at(d) else smap.get("building", "building")
        else:
            status = smap.get("planned" if mine else "intent")
        rows.append({"key": e["id"], "kind": "epic", f["name"]: e["name"], f["status"]: status})
    rows += stories
    for bucket in ("now", "next"):
        for p in plans.get(bucket) or []:
            sid = L.work_id(p.get("name"))
            for t in p.get("tasks") or []:
                if _task_of(sid, L.work_id(t.get("name"))):
                    rows.append({"key": L.work_id(t["name"]), "kind": "task", f["name"]: t["name"],
                                 f["status"]: tmap.get(t.get("state"), t.get("state")),
                                 rel["story"]: p["name"]})
    for r in _releases(d):
        row = {"key": r["id"], "kind": "release", f["name"]: r["name"],
               f["status"]: cfg["release_status_map"].get(r["stage"], r["stage"])}
        if f.get("stage"):
            row[f["stage"]] = r["stage"]
        rows.append(row)
    return rows


def not_mirrored(d):
    """Tasks of live items that relational mode does not mirror, as 'E-01.S2: name'.

    Covers a task with no id, one whose id names another story, and one carrying a
    finding or story id: said, never silent. Pure.
    """
    out = []
    for bucket in ("now", "next"):
        for p in (d.get("plans") or {}).get(bucket) or []:
            sid = L.work_id(p.get("name"))
            for t in p.get("tasks") or []:
                if not _task_of(sid, L.work_id(t.get("name"))):
                    out.append("%s: %s" % (sid or p.get("name"), t.get("name")))
    return out


def relational_faults(d, root=None):
    """Why a plan cannot be mirrored relationally, as FAIL strings; [] means it can."""
    out = []
    if (d.get("meta") or {}).get("naming") != "work-ids":
        out.append("meta.tracker.relational keys rows by work id — set meta.naming to \"work-ids\"")
    for key, good in (("epics", _epics(d)), ("releases", _releases(d))):
        for i, e in enumerate(d.get(key) or []):
            if not any(e is g for g in good):
                out.append("%s[%d] is malformed (id, name%s must be strings); it is not mirrored"
                           % (key, i, ", stage" if key == "releases" else ""))
    epics = {e["id"] for e in _epics(d)}
    known_ids = _known_names(root, d)[0]
    seen = {}
    for r in _releases(d):
        for s in r.get("stories") or []:
            if s in seen:
                out.append("story %s is in two releases (%s, %s)" % (s, seen[s], r["id"]))
            seen[s] = r["id"]
            if s not in known_ids:
                out.append("release %s lists story %s, which the plan does not hold" % (r["id"], s))
    for bucket in ("now", "next"):
        for p in (d.get("plans") or {}).get(bucket) or []:
            sid = L.work_id(p.get("name"))
            if sid in epics:
                out.append("item %s carries the declared epic id %s; a story id is E-NN.Sn" % (p.get("name"), sid))
            elif sid and sid.split(".")[0] not in epics:
                out.append("story %s: its epic %s is not declared in epics[]" % (sid, sid.split(".")[0]))
            for t in p.get("tasks") or []:
                tid = L.work_id(t.get("name"))
                if tid and not _task_of(sid, tid):
                    out.append("task %s sits under %s; a task id is its own story's id plus .T<n>" % (tid, sid))
    return out


def _known_names(root, d):
    """Every id and name the plan has ever held, and which of them are finished.

    Returns (ids, names, done_ids, done_names). Why: a tracker row for work that
    has rolled out of plan.json is history, not a stray, so it is not reported
    as 'not in the plan'; but if that work is finished its row must say Done.
    Finished = plans.done plus plan/archive/done.json.
    """
    plans = d.get("plans") or {}
    adir = os.path.join(L.paths(root)["dir"], L.ARCHIVE_DIRNAME) if root else None

    def archived(fn):
        if adir is None:
            return []
        try:
            v = json.load(open(os.path.join(adir, fn), encoding="utf-8"))
            return v if isinstance(v, list) else []
        except Exception:
            return []

    finished = list(plans.get("done") or []) + archived("done.json")
    live = list(plans.get("now") or []) + list(plans.get("next") or []) + archived("backlog.json")
    ids, names, done_ids, done_names = set(), set(), set(), set()
    for group, i_set, n_set in ((live, ids, names), (finished, done_ids, done_names)):
        for it in group:
            if isinstance(it, dict) and isinstance(it.get("name"), str):
                wid = L.work_id(it["name"])
                if wid:
                    i_set.add(wid)
                n_set.add(_norm(it["name"]))
                n_set.add(_norm(_title(it["name"])))
    return ids | done_ids, names | done_names, done_ids, done_names


def read_actual(path, cfg):
    """Load the rows the agent fetched. Returns (rows, error); one is None.

    Accepts only a bare JSON list of row objects, as fetched from the tracker.
    The object `expected` prints is refused: diffing the plan against itself
    would clear the gate without the tracker having been read. Every value of a
    declared field must be a plain string (or null for empty); a structured
    value would never equal the expected one and the fix would loop forever.
    """
    try:
        raw = json.load(open(path, encoding="utf-8"))
    except Exception as exc:
        return None, "cannot read %s: %s" % (path, exc)
    if isinstance(raw, dict) and "rows" in raw:
        return None, ("%s has the shape `expected` prints; fetch the rows from the tracker "
                      "through its connector and save that list instead" % path)
    if not isinstance(raw, list):
        return None, "%s must hold a JSON list of row objects fetched from the tracker" % path
    nf = cfg["fields"]["name"]
    for i, r in enumerate(raw):
        if not isinstance(r, dict) or not isinstance(r.get(nf), str):
            return None, "row %d of %s is not an object with a %r text field" % (i, path, nf)
        for fname in cfg["fields"].values():
            v = r.get(fname)
            if v is not None and not isinstance(v, str):
                return None, ("field %r of row %r is %s, not a plain string: flatten every "
                              "property to a plain string when fetching"
                              % (fname, r[nf], type(v).__name__))
    return raw, None


def expected_hash(rows, cfg):
    """A short hash of what is compared (key, name, status, stage): what a reconcile vouches for.

    Updated and Link are left out on purpose; they are not compared, so an
    unrelated plan edit must not make the mirror look stale.
    """
    f = cfg["fields"]
    cols = [f["name"], f["status"]] + ([f["stage"]] if f.get("stage") else [])
    if cfg.get("relational"):
        cols = ["kind"] + cols + [cfg["relations"][k] for k in ("epic", "story", "release")]
    body = json.dumps([[r["key"]] + [r.get(c) for c in cols] for r in rows], ensure_ascii=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def diff_rows(expected, actual, cfg, known):
    """Compare expected with actual rows. Returns a list of instruction strings; [] means clean.

    Rows are matched on the work id at the start of the name; a row lacking the
    id but matching the item's title (id and separators stripped) is matched
    too. The full name, the status and (when the adapter declares it) the stage
    are compared; Updated and Link are not. Rows for finished work outside the
    mirrored window must say the adapter's done value. Pure.
    """
    f = cfg["fields"]
    known_ids, known_names, done_ids, done_names = known
    done_value = cfg["status_map"]["done"]
    out, seen = [], {}
    for e in expected:
        seen.setdefault(e["key"], []).append(e)
    uniq = []
    for key, group in seen.items():
        if len(group) > 1:
            kind = "work id" if L.work_id(group[0][f["name"]]) else "name"
            out.append("%d plan items share the %s '%s'; give them distinct work ids" % (len(group), kind, key)
                       if kind == "work id" else
                       "%d plan items share the name '%s'; give them work ids" % (len(group), key))
        uniq.append(group[0])
    by_id, no_id = {}, []
    for r in actual:
        wid = L.work_id(r[f["name"]])
        if wid:
            by_id.setdefault(wid, []).append(r)
        else:
            no_id.append(r)
    used = []
    for e in uniq:
        if len(seen[e["key"]]) > 1:
            used.extend(r for r in actual if _norm(r[f["name"]]) == _norm(e[f["name"]]))
            continue
        wid = L.work_id(e[f["name"]])
        no_id_match = False
        if wid:
            hits = list(by_id.get(wid, []))
            if not hits:
                t = _norm(_title(e[f["name"]]))
                hits = [r for r in no_id if _norm(_title(r[f["name"]])) == t and r not in used]
                no_id_match = bool(hits)
        else:
            hits = [r for r in actual if _norm(r[f["name"]]) == _norm(e[f["name"]])]
        if not hits:
            cols = [f["name"], f["status"], f.get("stage"), f.get("updated"), f.get("link")]
            out.append("create row: %s" % ", ".join("%s=%r" % (k, e[k]) for k in cols if k and k in e))
            continue
        used.extend(hits)
        if len(hits) > 1:
            out.append("duplicate rows for %r (%d found): archive all but one" % (e["key"], len(hits)))
        r = hits[0]
        shown = r[f["name"]]
        if no_id_match:
            out.append("rename '%s' to start with its work id: '%s'" % (shown, e[f["name"]]))
        elif L.nfc_text(shown) != L.nfc_text(e[f["name"]]):
            out.append("rename '%s' to '%s'" % (shown, e[f["name"]]))
        for k in ("status", "stage"):
            if f.get(k) and L.nfc_text(r.get(f[k])) != L.nfc_text(e[f[k]]):
                out.append("set %s of '%s' to '%s'" % (f[k], shown, e[f[k]]))
    for r in actual:
        if any(r is u for u in used):
            continue
        nm = r[f["name"]]
        wid = L.work_id(nm)
        names = (_norm(nm), _norm(_title(nm)))
        if wid and wid in done_ids or any(n in done_names for n in names):
            if r.get(f["status"]) != done_value:
                out.append("set %s of '%s' to '%s'" % (f["status"], nm, done_value))
        elif (wid and wid in known_ids) or any(n in known_names for n in names):
            continue
        else:
            out.append("row '%s' not in the plan: archive or add to the plan" % nm)
    return out


def record(root, d, cfg, drift):
    """Write plan/tracker-state.json: when, how much drift, and a hash of the expected rows compared."""
    L.atomic_write(L.tracker_state_path(root), json.dumps(
        {"at": L.utc_now(), "drift": drift, "kind": cfg["kind"],
         "plan_updated": (d.get("meta") or {}).get("updated"),
         "expected_hash": expected_hash(expected_rows(d, cfg, root), cfg)}, indent=2) + "\n")


def reconcile(actual_path, quiet=False):
    """Run one reconcile against a fetched file. Prints the instructions; returns the exit code.

    Side effect: records the reconcile in plan/tracker-state.json when the
    input was readable (clean or drifting). Unreadable input records nothing.
    """
    p = L.paths()
    d = L.load(p["root"])
    cfg, err = L.tracker_config(d, p["root"])
    if err or cfg is None:
        print("  tracker: %s" % (err or "meta.tracker is not set in plan.json"))
        return 2
    actual, err = read_actual(actual_path, cfg)
    if err:
        print("  tracker: %s -- nothing was compared" % err)
        return 2
    exp = expected_rows(d, cfg, p["root"])
    known = _known_names(p["root"], d)
    todo = diff_rows(exp, actual, cfg, known)
    record(p["root"], d, cfg, len(todo))
    if todo:
        print("  tracker: %d difference(s) from the plan; carry out each, then fetch the rows and diff again:"
              % len(todo))
        for t in todo:
            print("    - %s" % t)
        return 1
    print("  tracker: OK -- %d expected row(s) match %s" % (len(exp), cfg["kind"]))
    return 0


def next_step(d, cfg, root=None):
    """Print the expected-rows summary and the exact next step for the agent. Returns 0."""
    exp = expected_rows(d, cfg, root)
    f = cfg["fields"]
    print("  tracker: %s %s -- %d expected row(s):" % (cfg["kind"], cfg["target"], len(exp)))
    for r in exp:
        print("    - %s" % " | ".join(r[f[k]] for k in ("name", "status", "stage") if f.get(k) and f[k] in r))
    print("  next: fetch the rows -- %s" % cfg["fetch"])
    print("        save them to a file, then run: sync.py --tracker --actual <file>")
    return 0


def main():
    if not L.has_plan():
        print("  tracker: no plan in this project (plan/plan.json); nothing to mirror")
        return 2
    args = sys.argv[1:]
    cmd = args[0] if args else ""
    d = L.load()
    cfg, err = L.tracker_config(d, L.paths()["root"])
    if err or cfg is None:
        print("  tracker: %s" % (err or "meta.tracker is not set in plan.json"))
        return 2
    if cmd == "expected":
        out = {"tracker": cfg["kind"], "target": cfg["target"],
               "plan_updated": (d.get("meta") or {}).get("updated"),
               "fetch": cfg["fetch"], "rows": expected_rows(d, cfg, L.paths()["root"])}
        if cfg["relational"]:
            out["not_mirrored"] = not_mirrored(d)
        print(json.dumps(out, indent=2, ensure_ascii=False))
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
