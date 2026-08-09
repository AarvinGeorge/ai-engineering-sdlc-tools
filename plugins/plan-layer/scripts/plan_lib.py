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


def save(data, root=None):
    p = paths(root)["src"]
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


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
