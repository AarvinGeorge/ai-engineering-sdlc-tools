#!/usr/bin/env python3
"""Pause the work with a handover note, or resume it.

  pause.py             write plan/HANDOFF.md, set meta.paused, re-render
  pause.py --resume    clear meta.paused; HANDOFF.md stays, marked resumed

Standard practice for handing work to whoever picks it up next (the same
person after a break, or a fresh session) is an on-call handover note: what is
active, what comes next, what is open, what will bite. HANDOFF.md is that note,
written so a fresh session can start from it. Every figure in it is read from
the clock, git and the gate at the moment of writing, never recalled, and the
note says when ("numbers here were read at <time>; re-read before citing").

While paused, the tracker mirror shows active items as the adapter's "Paused"
value and brief.py opens the session with a PAUSED line. Pausing bumps
meta.updated (the plan changed) and re-renders so the page is never stale.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_lib as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
HANDOFF = "HANDOFF.md"


def now_utc():
    """The current UTC time as ISO-8601 with a Z, read from the clock."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_facts(root):
    """Branch, HEAD and uncommitted-file count measured now, as one line.

    Returns "not a git repo" outside a work tree. The count is taken before
    pause.py changes anything, so it is the work's own uncommitted state.
    """
    if L.git(root, "rev-parse", "--is-inside-work-tree") != "true":
        return "not a git repo"
    branch = L.git(root, "rev-parse", "--abbrev-ref", "HEAD") or "(unknown)"
    head = L.git(root, "rev-parse", "--short", "HEAD")
    subject = L.git(root, "log", "-1", "--format=%s")
    n = len([ln for ln in L.git(root, "status", "--porcelain").splitlines() if ln.strip()])
    head_s = "%s %s" % (head, subject) if head else "no commits yet"
    return "branch %s, HEAD %s, %d uncommitted file(s)" % (branch, head_s, n)


def render_handoff(d, git_line, read_at, fails, drifts):
    """Compose the note. Inputs: plan dict, git line, clock reading, gate FAILs and DRIFTs. Returns text."""
    plans = d.get("plans") or {}
    meta = d.get("meta") or {}
    out = ["# Handoff: %s" % (meta.get("project") or "project"), "",
           "Written at %s. Start here, then read plan/plan.json by key." % read_at, "",
           "## Where things stand", "",
           "- Git: %s (uncommitted count taken before this note's own edits to plan/)" % git_line,
           "- Gate: %d FAIL, %d DRIFT" % (len(fails), len(drifts)), "",
           "## ACTIVE NOW", ""]
    now = plans.get("now") or []
    for p in now:
        out.append("- [%s] %s: %s" % (p.get("stage"), p.get("name"), p.get("status") or "(no status)"))
        open_tasks = [t.get("name") for t in p.get("tasks") or [] if t.get("state") != "done"]
        if open_tasks:
            out.append("  - still to do: %s" % "; ".join(map(str, open_tasks[:8])))
    if not now:
        out.append("- nothing recorded as active")
    out += ["", "## Resume order (now, then next)", ""]
    order = [("now", p) for p in now] + [("next", p) for p in plans.get("next") or []]
    for i, (b, p) in enumerate(order, 1):
        out.append("%d. %s [%s, %s]" % (i, p.get("name"), b, p.get("stage")))
    if not order:
        out.append("(nothing queued)")
    out += ["", "## Open questions and parked", ""]
    parked = d.get("parked") or []
    for q in parked:
        out.append("- %s %s (decide when: %s)" % (q.get("id"), q.get("q"), q.get("trigger")))
    if not parked:
        out.append("- none parked")
    out += ["", "## Traps", ""]
    traps = ["Invariant not holding: %s (%s)" % (i.get("rule"), i.get("state"))
             for i in d.get("invariants") or [] if i.get("state") != "holding"]
    traps += ["Gate FAIL: %s" % m for m in fails] + ["Drift: %s" % m for m in drifts]
    out += ["- %s" % t for t in traps] or ["- none found by the gate"]
    out += ["", "---", "numbers here were read at %s; re-read before citing." % read_at, ""]
    return "\n".join(out)


def pause(p):
    """Write the note, set meta.paused, bump meta.updated, re-render. Returns 0."""
    root = p["root"]
    at = now_utc()
    git_line = git_facts(root)
    d = L.load(root)
    d.setdefault("meta", {})["paused"] = {"at": at}
    d["meta"]["updated"] = at
    L.save(d, root)
    subprocess.run([sys.executable, os.path.join(HERE, "render.py")], capture_output=True)
    import check
    fails, drifts, _ = check.run(root)
    L.atomic_write(os.path.join(p["dir"], HANDOFF),
                   render_handoff(d, git_line, at, [m for _, m in fails], [m for _, m in drifts]))
    print("  pause: wrote %s (paused at %s)" % (os.path.join(os.path.relpath(p["dir"], root), HANDOFF), at))
    print("  pause: the gate reads %d FAIL, %d DRIFT" % (len(fails), len(drifts)))
    print("  REMINDER: stop this work's recurring loops and scheduled tasks (cron, /loop, "
          "scheduled routines) now, so nothing keeps running against a paused plan.")
    return 0


def resume(p):
    """Clear meta.paused, mark the note resumed, re-render. Returns 0; a no-op when not paused."""
    root = p["root"]
    d = L.load(root)
    if "paused" not in (d.get("meta") or {}):
        print("  resume: the plan is not paused; nothing changed")
        return 0
    at = now_utc()
    del d["meta"]["paused"]
    d["meta"]["updated"] = at
    L.save(d, root)
    subprocess.run([sys.executable, os.path.join(HERE, "render.py")], capture_output=True)
    note = os.path.join(p["dir"], HANDOFF)
    if os.path.isfile(note):
        lines = open(note, encoding="utf-8").read().split("\n")
        lines[2:2] = ["**RESUMED at %s.** This note is history now; re-read the plan." % at, ""]
        L.atomic_write(note, "\n".join(lines))
    print("  resume: meta.paused cleared at %s; restart any loops or scheduled tasks you stopped" % at)
    return 0


def main():
    if not L.has_plan():
        return 0
    p = L.paths()
    return resume(p) if "--resume" in sys.argv else pause(p)


if __name__ == "__main__":
    sys.exit(main())
