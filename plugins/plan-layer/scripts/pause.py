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
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_lib as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
HANDOFF = "HANDOFF.md"
DECISION_ID = re.compile(r"\bD-[0-9]{3,}\b")


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


def git_per_item(root, d):
    """What it does: for each active item in plans.now, names the branches whose name holds
    its epic slug and the last commit whose message names its work id.
    Use when: the handoff must say where each active item's code is, read now, never recalled.
    Inputs: project root; the plan dict (only plans.now is read, plans.next is not).
    Output: list of markdown bullet lines; "- nothing active" when plans.now has no work id.
    Side effects: read-only git.
    Role: fact for the reader of the handoff; decides nothing.
    """
    out = []
    branches = L.git(root, "branch", "--list", "--format=%(refname:short)").splitlines()
    for p in (d.get("plans") or {}).get("now") or []:
        wid = L.work_id(p.get("name"))
        if not wid:
            continue
        slug = wid.split(".")[0].lower()
        slug_re = re.compile(r"(^|[^0-9a-z])%s([^0-9]|$)" % re.escape(slug))
        mine = [b for b in branches if slug_re.search(b.lower())] or ["no branch names %s" % slug]
        last = L.git(root, "log", "-1", "--format=%h %s", "-E",
                     "--grep=%s([^0-9]|$)" % re.escape(wid))
        out.append("- %s: branches %s; last commit naming it: %s"
                   % (wid, ", ".join(mine), last or "none"))
    return out or ["- nothing active"]


def decisions_since(root, cfg, since_head):
    """What it does: lists decision ids on lines added to the decision log since the last
    handoff's HEAD, else since the merge-base with the base branch.
    Use when: the handoff must carry decisions made since the previous one.
    Inputs: project root; resolved controller config; the previous handoff's HEAD or None.
    Output: list of markdown bullet lines; a bullet saying why when it cannot measure.
    Ids added but not yet committed at the last handoff are listed again next time (the safe
    direction). An unmeasurable diff says so and never reads "none": a missing or untracked
    log, or a base with no merge-base, gives "cannot measure"; a previous head git no longer
    knows falls back to the merge-base and says so.
    Side effects: read-only git.
    Role: fact for the reader of the handoff; decides nothing.
    """
    log = cfg.get("decision_log")
    if not log:
        return ["- no decision log configured (meta.controller.decision_log)"]
    if not os.path.isfile(os.path.join(root, log)):
        return ["- cannot measure: %s is not a file" % log]
    if not L.git(root, "ls-files", "--error-unmatch", log):
        return ["- cannot measure: %s is not tracked by git" % log]
    note = ""
    if since_head and not L.git(root, "cat-file", "-t", since_head + "^{commit}"):
        note = " (the last handoff's head %s is unknown to git; used the merge-base with %s)" % (
            since_head[:7], cfg["base"])
        since_head = None
    since = since_head or L.git(root, "merge-base", cfg["base"], "HEAD")
    if not since:
        return ["- cannot measure: no earlier handoff and no merge-base with %r" % cfg["base"]]
    added = [ln[1:] for ln in L.git(root, "diff", since, "--", log).splitlines()
             if ln.startswith("+") and not ln.startswith("+++")]
    ids = sorted({m for ln in added for m in DECISION_ID.findall(ln)})
    return ["- added to %s since %s: %s%s" % (log, since[:7], ", ".join(ids) or "none", note)]


def render_handoff(d, git_line, read_at, fails, drifts, extra=None):
    """Compose the note. Inputs: plan dict, git line, clock reading, gate FAILs and DRIFTs,
    and optionally extra lines placed just before the Traps section. Returns text."""
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
    if extra:
        out += [""] + list(extra)
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
    at = L.utc_now()
    git_line = git_facts(root)
    d = L.load(root)
    cfg, _ = L.controller_config(d)
    head = L.git(root, "rev-parse", "HEAD")
    d.setdefault("meta", {})["paused"] = {"at": at}
    d["meta"]["updated"] = at
    L.save(d, root)
    subprocess.run([sys.executable, os.path.join(HERE, "render.py")], capture_output=True)
    import check
    fails, drifts, summary = check.run(root, event="pause")
    extra, found = None, []
    if cfg:
        found = summary.get("controller") or []
        prev = ((L.controller_state(root) or {}).get("handoff") or {}).get("head")
        extra = ["## Reconcile (the controller's diff at %s)" % at, ""]
        extra += ["- [%s] %s: %s" % (f["level"], f["check"], f["message"]) for f in found] \
            or ["- clean: nothing to reconcile"]
        extra += ["", "## Git per active item", ""] + git_per_item(root, d)
        extra += ["", "## Decisions since the last handoff", ""] + decisions_since(root, cfg, prev)
        extra += ["- Agent step: search this session's transcript for decisions given in passing "
                  "and append each to the decision log before ending.", ""]
        stp = L.controller_state_path(root)
        st = L.controller_state(root)
        if st is None and os.path.exists(stp):
            extra.insert(-1, "- handoff record not written: controller-state.json unreadable")
        else:
            st = st or {}
            st["handoff"] = {"at": at, "head": head}
            L.atomic_write(stp, json.dumps(st, indent=2) + "\n")
    L.atomic_write(os.path.join(p["dir"], HANDOFF),
                   render_handoff(d, git_line, at, [m for _, m in fails], [m for _, m in drifts],
                                  extra))
    for f in found:
        print("  CONTROLLER: [%s] %s" % (f["level"], f["message"]))
    print("  pause: wrote %s (paused at %s)" % (os.path.join(os.path.relpath(p["dir"], root), HANDOFF), at))
    print("  pause: the gate reads %d FAIL, %d DRIFT" % (len(fails), len(drifts)))
    print("  REMINDER: stop this work's recurring loops and scheduled tasks (cron, /loop, "
          "scheduled routines) now, so nothing keeps running against a paused plan.")
    if L.tracker_config(d, root)[0]:
        print("  NEXT: run sync.py --tracker so the tracker shows the active items as Paused")
    return 0


def resume(p):
    """Clear meta.paused, mark the note resumed, re-render. Returns 0; a no-op when not paused."""
    root = p["root"]
    d = L.load(root)
    if "paused" not in (d.get("meta") or {}):
        print("  resume: the plan is not paused; nothing changed")
        return 0
    at = L.utc_now()
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
    if L.tracker_config(d, root)[0]:
        print("  NEXT: run sync.py --tracker so the tracker shows the items as active again")
    return 0


USAGE = "usage: pause.py [--resume]   (no other arguments)"


def main():
    if [a for a in sys.argv[1:] if a != "--resume"] or sys.argv[1:].count("--resume") > 1:
        print(USAGE)
        return 2
    if not L.has_plan():
        return 0
    p = L.paths()
    return resume(p) if "--resume" in sys.argv else pause(p)


if __name__ == "__main__":
    sys.exit(main())
