#!/usr/bin/env python3
"""Shared plumbing for plan-layer. Standard library only, on purpose.

Zero dependencies is a feature, not an aesthetic: this runs inside a session
hook on someone else's machine. A missing package would turn a briefing into a
stack trace, and a tool that breaks a session gets uninstalled.

Everything here is about answering one question reliably -- where is this
project's plan, and does it exist? -- so the three scripts cannot disagree.
"""
import json
import os
import re
import subprocess
import tempfile

PLAN_DIRNAME = "plan"
PLAN_FILENAME = "plan.json"
PAGE_FILENAME = "index.html"
CONFIG_FILENAME = ".plan-layer.json"


def project_root(start=None):
    """The directory the plan belongs to.

    CLAUDE_PROJECT_DIR is what Claude Code sets and is authoritative when
    present. Otherwise walk up looking for a plan directory, then a git root,
    then give up and use the cwd. Walking up matters because scripts get run
    from subdirectories.
    """
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and os.path.isdir(env):
        return os.path.abspath(env)

    cur = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.isfile(os.path.join(cur, PLAN_DIRNAME, PLAN_FILENAME)):
            return cur
        if os.path.isdir(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return os.path.abspath(start or os.getcwd())
        cur = parent


def config(root):
    """Optional per-project overrides. Absent is the normal case."""
    p = os.path.join(root, CONFIG_FILENAME)
    if os.path.isfile(p):
        try:
            return json.load(open(p))
        except Exception:
            return {}
    return {}


def paths(root=None):
    """Where the plan, the page and any project-supplied figures live."""
    root = root or project_root()
    cfg = config(root)
    pdir = os.path.join(root, cfg.get("plan_dir", PLAN_DIRNAME))
    return {
        "root": root,
        "dir": pdir,
        "src": os.path.join(pdir, cfg.get("plan_file", PLAN_FILENAME)),
        "out": os.path.join(pdir, cfg.get("page_file", PAGE_FILENAME)),
        "figures": os.path.join(pdir, "figures.py"),
    }


def has_plan(root=None):
    """False means this project has not opted in.

    Every entry point checks this and exits quietly. A layer that announces
    itself in projects that never asked for it is a layer people uninstall.
    """
    return os.path.isfile(paths(root)["src"])


def load(root=None):
    return json.load(open(paths(root)["src"], encoding="utf-8"))


def atomic_write(path, text):
    """Replace a file's contents in one step, or not at all.

    `open(path, "w")` truncates immediately, so an interruption between the
    truncate and the final byte leaves a half-written file. For a generated
    page that is annoying. For plan.json -- the source of truth this whole
    tool exists to protect -- it is data loss, and it was reproducible: a
    Ctrl-C mid-write left the file unparseable.

    Writing to a sibling temp file and renaming means a reader sees either the
    old contents or the new ones, never a mixture. os.replace is atomic on
    POSIX, and the temp file is in the same directory so the rename cannot
    cross a filesystem boundary. fsync before the rename so a power loss
    cannot leave the rename durable while the contents are not.
    """
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".plan-layer-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def save(data, root=None):
    atomic_write(paths(root)["src"],
                 json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def git(root, *args):
    """Run git in the project. Returns "" on any failure.

    rstrip the trailing newline ONLY. A bare .strip() eats the leading space of
    `git status --porcelain`'s fixed-width status column on the first line,
    shifting every path by one character -- a bug that silently misfiles paths.
    """
    try:
        r = subprocess.run(["git"] + list(args), cwd=root,
                           capture_output=True, text=True, timeout=10)
        return r.stdout.rstrip("\n") if r.returncode == 0 else ""
    except Exception:
        return ""


def load_figures(root=None):
    """Import the project's own figures module, if it supplies one.

    Diagrams are the least generic part of a plan page -- they are about one
    project's specific mechanism -- so the engine never ships any. A project
    that wants them drops a figures.py next to plan.json exposing
    build(data) -> html string. Absent, the page simply has no figure section.
    """
    p = paths(root)
    if not os.path.isfile(p["figures"]):
        return None
    import importlib.util
    try:
        spec = importlib.util.spec_from_file_location("plan_figures", p["figures"])
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod if hasattr(mod, "build") else None
    except Exception as exc:
        print("  warning: %s failed to load (%s); rendering without figures"
              % (p["figures"], exc))
        return None


DEFAULT_CYCLE = {
    "what": ("Every unit of work moves through these six stages. A stage is only "
             "complete when its evidence exists — not when it feels done."),
    "stages": [
        {"id": "intent", "name": "Intent", "who": "Human",
         "done_when": "The outcome is named. Not the method — the outcome.",
         "skipped_looks_like": "Building something nobody asked for."},
        {"id": "grounded", "name": "Grounded", "who": "Agent",
         "done_when": "Checked against the real system and measured. Every claim has a "
                      "source read in the same pass.",
         "skipped_looks_like": "Planning against how we think it works."},
        {"id": "planned", "name": "Planned", "who": "Agent",
         "done_when": "A plan document exists with verifiable steps and an explicit "
                      "out-of-scope list.",
         "skipped_looks_like": "Scope creep, and no way to tell when it is finished."},
        {"id": "building", "name": "Building", "who": "Agent",
         "done_when": "The steps are executed, one at a time, with the tree kept clean.",
         "skipped_looks_like": "Nothing — this is the stage nobody skips."},
        {"id": "verified", "name": "Verified", "who": "Agent",
         "done_when": "The gate is green and the evidence is shown, not asserted.",
         "skipped_looks_like": "A green result that tested nothing — the most dangerous "
                               "direction of error."},
        {"id": "recorded", "name": "Recorded", "who": "Agent",
         "done_when": "plan.json updated, page re-rendered, decisions logged.",
         "skipped_looks_like": "The next session re-derives what this one already learned."},
    ],
}

# --------------------------------------------------------------------------
# Rolling (0.14.0). The live plan shows this month; older records move, in
# full, into <plan_dir>/archive/*.json. The RULES live here so roll.py (which
# moves) and check.py (which says when moving is due) can never disagree.
# --------------------------------------------------------------------------
ARCHIVE_DIRNAME = "archive"
ROLL_DEFAULTS = {"keep_done": 8, "keep_log": 10, "keep_next": 8}


def roll_config(root=None):
    """Per-project overrides under "roll" in .plan-layer.json; absent is normal."""
    cfg = dict(ROLL_DEFAULTS)
    cfg.update((config(root or project_root()).get("roll") or {}))
    return cfg


def rollable(d, cfg):
    """What roll.py would move, as three lists. Pure: reads d, writes nothing.

    The queue keeps its first keep_next items PLUS the earliest queued item of
    any capability that would otherwise have nothing queued -- the gate reads
    "blocked with nothing queued" as drift, and a rolled-off item must never
    manufacture that signal.
    """
    plans = d.get("plans") or {}
    done = plans.get("done") or []
    log = (d.get("meta") or {}).get("changelog") or []
    nxt = plans.get("next") or []
    keep, seen = [], set()
    for i, it in enumerate(nxt):
        cap = str(it.get("capability"))
        if i < cfg["keep_next"] or cap not in seen:
            keep.append(it)
            seen.add(cap)
    return {
        "done": done[:-cfg["keep_done"]] if len(done) > cfg["keep_done"] else [],
        "changelog": log[:-cfg["keep_log"]] if len(log) > cfg["keep_log"] else [],
        # By identity, not equality: two queued items that happen to be equal
        # dicts are two items, and the second must still roll off.
        "next": [it for it in nxt if not any(it is k for k in keep)],
        "keep_next": keep,
    }


def _append_archive(path, items):
    """Append items to an archive file, skipping exact duplicates. Returns how many were new."""
    if not items:
        return 0
    have = json.load(open(path, encoding="utf-8")) if os.path.isfile(path) else []
    keys = {json.dumps(x, sort_keys=True, ensure_ascii=False) for x in have}
    new = [x for x in items if json.dumps(x, sort_keys=True, ensure_ascii=False) not in keys]
    atomic_write(path, json.dumps(have + new, indent=1, ensure_ascii=False) + "\n")
    return len(new)


def roll(root=None):
    """Move what `rollable` says is due into plan/archive/, in full. The one writer.

    roll.py and sync.py both call this, so there is one roll rule and one way
    of applying it. Nothing is deleted: archive files are append-only and
    de-duplicated, so a second run is a no-op. Returns the counts moved and the
    file size before and after (bytes); all zero counts means nothing was due.
    """
    p = paths(root)
    cfg = roll_config(p["root"])
    d = load(p["root"])
    before = os.path.getsize(p["src"])
    r = rollable(d, cfg)
    out = {"done": len(r["done"]), "changelog": len(r["changelog"]), "next": len(r["next"]),
           "before": before, "after": before}
    if not (r["done"] or r["changelog"] or r["next"]):
        return out
    adir = os.path.join(p["dir"], ARCHIVE_DIRNAME)
    os.makedirs(adir, exist_ok=True)
    out["new"] = (_append_archive(os.path.join(adir, "done.json"), r["done"]),
                  _append_archive(os.path.join(adir, "changelog.json"), r["changelog"]),
                  _append_archive(os.path.join(adir, "backlog.json"), r["next"]))
    if r["done"]:
        d["plans"]["done"] = d["plans"]["done"][-cfg["keep_done"]:]
    if r["changelog"]:
        d["meta"]["changelog"] = d["meta"]["changelog"][-cfg["keep_log"]:]
    if r["next"]:
        d["plans"]["next"] = r["keep_next"]
    save(d, p["root"])
    out["after"] = os.path.getsize(p["src"])
    return out


# --------------------------------------------------------------------------
# Size budget and mode (0.16.0). Read from the plan itself, from one place, so
# check.py and anything else that asks cannot disagree.
SIZE_BUDGET_KB_DEFAULT = 200
MODES = ("full", "light")


def size_budget_kb(d):
    """meta.size_budget_kb when it is a positive whole number, else the default.

    The gate FAILs on a value that is present but nonsense (see check.py), so
    falling back here never hides a typo.
    """
    v = (d.get("meta") or {}).get("size_budget_kb")
    if isinstance(v, int) and not isinstance(v, bool) and v > 0:
        return v
    return SIZE_BUDGET_KB_DEFAULT


def mode(d):
    """'light' or 'full'. Absent means full, so every plan written before 0.16.0 is unchanged."""
    return "light" if (d.get("meta") or {}).get("mode") == "light" else "full"


# --------------------------------------------------------------------------
# Work-id naming (0.17.0), opt-in through meta.naming. One pattern, read from
# here, so the gate and anything else that names work cannot disagree.
#   Epic E-NN · Story E-NN.Sn · Task E-NN.Sn.Tn · Finding E-NN.Fn · Release R-NN
# Initiatives (I-n) and decisions (D-NNN) are not work items, so a now/next
# item is never named by one alone. ASCII digits only. The id ends at the end
# of the name, whitespace, ':', '·', ',', ';' or '-' (so "E-01-search" and
# "R-04-hotfix" pass); "E-01x", "E-01.S" and "E-01)" do not.
NAMINGS = ("work-ids",)
WORK_ID = re.compile(r"^(?:E-[0-9]{2,}(?:\.S[0-9]+(?:\.T[0-9]+)?|\.F[0-9]+)?|R-[0-9]{2,})(?=$|[\s:·,;-])")


def has_work_id(name):
    """True when an item name starts with an epic, story, task, finding or release id."""
    return isinstance(name, str) and bool(WORK_ID.match(name))


def work_id(name):
    """The leading work id of an item name ('E-01.S2' from 'E-01.S2 Login page'), else None.

    Same pattern as has_work_id, so the gate and the tracker mirror cannot
    disagree about what an id is.
    """
    m = WORK_ID.match(name) if isinstance(name, str) else None
    return m.group(0) if m else None


# --------------------------------------------------------------------------
# Tracker mirror and pause. One reading of meta.tracker / meta.paused, shared
# by tracker.py, pause.py, brief.py and the gate. The adapters are data files in
# <plugin>/trackers/<kind>.json; the reconcile record is plan/tracker-state.json
# (outside plan.json, so it never counts against the size budget).
TRACKERS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trackers")
TRACKER_STATE_FILENAME = "tracker-state.json"
TRACKER_RECENT_DONE_DEFAULT = 5
_REQUIRED_FIELDS = ("name", "status")


def nfc_text(text):
    """Text in Unicode NFC with runs of whitespace collapsed to one space.

    Why: a tracker may hand back the same name in decomposed form (NFD); it
    looks identical, so comparing raw would never converge. Every comparison of
    names, titles and values goes through this one helper. Non-strings pass through.
    """
    import unicodedata
    if not isinstance(text, str):
        return text
    return " ".join(unicodedata.normalize("NFC", text).split())


def utc_now():
    """The current UTC time as ISO-8601 with a Z, read from the clock. The one formatter."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def tracker_config(d, root=None):
    """Resolve meta.tracker against its adapter. Returns (config, error); one is None.

    Why: the gate, tracker.py and sync.py must all read the same effective
    fields and status map. The adapter is looked up at <plan dir>/trackers/<kind>.json
    first (a project's own, which a plugin update never touches), then in the
    plugin's trackers/. Only name and status are required fields; stage, updated
    and link are mirrored and compared only when the adapter declares them.
    config = {kind, target, fields, status_map,
    recent_done, fetch}. Overrides in meta.tracker are merged over the adapter.
    Absent meta.tracker returns (None, None): the feature is off.
    """
    meta = d.get("meta") or {}
    if "tracker" not in meta:
        return None, None
    t = meta["tracker"]
    if not isinstance(t, dict):
        return None, "meta.tracker is %r — it must be an object {kind, target}" % (t,)
    kind, target = t.get("kind"), t.get("target")
    if not isinstance(kind, str) or not re.fullmatch(r"[a-z0-9_-]+", kind or ""):
        return None, "meta.tracker.kind is %r — it must name an adapter file in trackers/" % (kind,)
    if not isinstance(target, str) or not target.strip():
        return None, "meta.tracker.target is %r — it must be the tracker's database url or id" % (target,)
    adapter, tried = None, []
    for base in (os.path.join(paths(root)["dir"], "trackers"), TRACKERS_DIR):
        path = os.path.join(base, kind + ".json")
        if os.path.isfile(path):
            try:
                adapter = json.load(open(path, encoding="utf-8"))
            except Exception as exc:
                return None, "adapter %s does not parse: %s" % (path, exc)
            if not isinstance(adapter, dict):
                return None, "adapter %s must be a JSON object" % path
            break
        tried.append(path)
    if adapter is None:
        return None, "meta.tracker.kind %r has no adapter (looked in plan/trackers/ and the plugin's trackers/)" % kind
    fields = dict(adapter.get("fields") or {})
    smap = dict(adapter.get("status_map") or {})
    for key, bag in (("fields", fields), ("status_map", smap)):
        over = t.get(key)
        if over is None:
            continue
        if not (isinstance(over, dict) and all(isinstance(k, str) and isinstance(v, str) and v
                                               for k, v in over.items())):
            return None, "meta.tracker.%s must be an object of non-empty strings" % key
        bag.update(over)
    missing = [k for k in _REQUIRED_FIELDS if not fields.get(k)]
    if missing or not smap.get("paused") or not smap.get("done"):
        return None, "adapter %r is incomplete (fields name and status, status_map paused and done)" % kind
    rd = t.get("recent_done", TRACKER_RECENT_DONE_DEFAULT)
    if not (isinstance(rd, int) and not isinstance(rd, bool) and rd >= 0):
        return None, "meta.tracker.recent_done is %r — it must be a whole number, 0 or more" % (rd,)
    return {"kind": kind, "target": target, "fields": fields, "status_map": smap,
            "recent_done": rd, "fetch": adapter.get("fetch", "")}, None


def tracker_state_path(root=None):
    """Where the last reconcile is recorded: <plan dir>/tracker-state.json."""
    return os.path.join(paths(root)["dir"], TRACKER_STATE_FILENAME)


def tracker_state(root=None):
    """The recorded reconcile {at, drift, plan_updated, kind}, or None when absent or unreadable."""
    try:
        v = json.load(open(tracker_state_path(root), encoding="utf-8"))
        return v if isinstance(v, dict) else None
    except Exception:
        return None


def paused_at(d):
    """meta.paused.at when the plan is validly paused, else None. Absent is the normal case."""
    p = (d.get("meta") or {}).get("paused")
    at = p.get("at") if isinstance(p, dict) else None
    if isinstance(at, str) and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z", at):
        return at
    return None


def archive_counts(root=None):
    """How many records sit in each archive file, for the page's section hints."""
    pdir = paths(root)["dir"]
    out = {}
    for name in ("done", "changelog", "backlog"):
        f = os.path.join(pdir, ARCHIVE_DIRNAME, name + ".json")
        if os.path.isfile(f):
            try:
                out[name] = len(json.load(open(f, encoding="utf-8")))
            except Exception:
                out[name] = None
    return out

# --------------------------------------------------------------------------
# Views (0.15.0): drawings published beside the page. A view is a spec file in
# the repository (the truth), a published URL (the pointer), and two facts read
# from the spec and from the delivery -- never typed: the revision the drawing
# was measured at (meta.repository.revision, an Archify primitive) and the
# SHA-256 of the spec bytes that were delivered. The gate compares both.
# --------------------------------------------------------------------------
import hashlib as _hashlib


def sha256_file(path):
    h = _hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def view_facts(root, view):
    """What the spec on disk says now: its sha256 and its declared revision.
    Returns {} when the spec is absent, so a caller can tell 'unknown' from 'differs'."""
    spec = view.get("spec")
    if not spec:
        return {}
    path = spec if os.path.isabs(spec) else os.path.join(root, spec)
    if not os.path.isfile(path):
        return {}
    out = {"spec_sha256": sha256_file(path)}
    try:
        meta = json.load(open(path, encoding="utf-8")).get("meta") or {}
        rev = (meta.get("repository") or {}).get("revision")
        if rev:
            out["revision"] = rev
    except Exception:
        pass
    return out

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
    if not isinstance(meta, dict) or "controller" not in meta:
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
    return {"one_writer": ow, "base": base.strip(), "decision_log": log, "rules": rules}, None


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
        rid = work_id(r.get("id")) if isinstance(r, dict) else None
        if rid and rid.startswith("R-"):
            out["releases"][rid] = r.get("stage")
    return out


def duplicate_ids(d):
    """Work ids carried by more than one item in plans.now and plans.next, or by more than one release, sorted. Pure."""
    seen, dup = set(), set()
    for bucket in ("now", "next"):
        for it in (d.get("plans") or {}).get(bucket) or []:
            wid = work_id(it.get("name")) if isinstance(it, dict) else None
            if wid in seen:
                dup.add(wid)
            elif wid:
                seen.add(wid)
    for r in d.get("releases") or []:
        rid = work_id(r.get("id")) if isinstance(r, dict) else None
        if rid and rid.startswith("R-"):
            if rid in seen:
                dup.add(rid)
            seen.add(rid)
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
    Raises ValueError when the record exists but is unreadable (never drops its other keys).
    """
    st = controller_state(root)
    if st is None:
        if os.path.exists(controller_state_path(root)):
            raise ValueError("plan/controller-state.json is unreadable — repair or remove it")
        st = {}
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
