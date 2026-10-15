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
