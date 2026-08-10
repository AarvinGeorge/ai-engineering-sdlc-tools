#!/usr/bin/env python3
"""Lint the plan itself. The gate that keeps the artifact honest.

render.py --check answers "does the PAGE match the DATA?". That is necessary
and not sufficient: it cannot see the failure that actually happens, which is
the data drifting from reality while both page and data agree with each other.

This checks two different things:

  FAIL  -- structural holes. The plan contradicts itself or is incomplete in a
           way that makes it misleading. These are objective.
  DRIFT -- signals that the plan is behind what has actually happened. These
           are heuristics on purpose; a heuristic that fires occasionally and
           is dismissed beats a check that never fires at all.

Deliberately NOT checked: whether the plan is TRUE. No script can know that.
The most this can do is make forgetting visible.

Stdlib only, no arguments needed.

  check.py           # human output, exit 1 on any FAIL
  check.py --json    # machine output for the session hooks
  check.py --strict  # exit 1 on DRIFT as well
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_lib as L  # noqa: E402

VALID_BUILD = {"done", "active", "partial", "not-started"}
VALID_PLAN = {"planned", "partial", "none"}
VALID_INV = {"holding", "at risk", "broken"}





def parse_iso(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def run(root=None):
    fails, drifts = [], []
    P = L.paths(root)
    root, SRC, OUT = P["root"], P["src"], P["out"]
    plan_dir = os.path.basename(P["dir"]) + "/"

    def git(*a):
        return L.git(root, *a)

    try:
        d = json.load(open(SRC, encoding="utf-8"))
    except Exception as exc:
        return [("FAIL", "plan.json does not parse: %s" % exc)], [], {}

    caps = d.get("capabilities", [])
    plans = d.get("plans", {})
    stage_ids = {s["id"] for s in (d.get("cycle") or L.DEFAULT_CYCLE).get("stages", [])}

    # ---------------------------------------------------------------- structure
    if not stage_ids:
        fails.append("cycle has no stages — plan items have nowhere to sit")

    for i, c in enumerate(caps):
        who = c.get("name") or "capability #%d" % i
        if c.get("build") not in VALID_BUILD:
            fails.append("%s: build=%r is not one of %s" % (who, c.get("build"), sorted(VALID_BUILD)))
        if c.get("plan") not in VALID_PLAN:
            fails.append("%s: plan=%r is not one of %s" % (who, c.get("plan"), sorted(VALID_PLAN)))
        # A capability claiming progress with no evidence is the exact shape of
        # a comfortable lie, so it is a hard failure rather than a nudge.
        if c.get("build") != "not-started" and not (c.get("evidence") or "").strip():
            fails.append("%s: claims build=%s but carries no evidence" % (who, c.get("build")))

    for p in plans.get("now", []):
        who = p.get("name") or "active item"
        for field in ("name", "status", "updated"):
            if not (p.get(field) or "").strip():
                fails.append("active item %r: missing %s" % (who, field))
        if p.get("stage") not in stage_ids:
            fails.append("active item %r: stage=%r is not a cycle stage" % (who, p.get("stage")))
        # Past 'planned' means a plan document was supposed to be written.
        if p.get("stage") in {"building", "verified", "recorded"} and not p.get("plan_file"):
            fails.append("active item %r: stage=%s but no plan_file — work is running "
                         "without a written plan" % (who, p.get("stage")))

    for p in plans.get("next", []):
        who = p.get("name") or "queued item"
        for field in ("name", "why", "unblocks"):
            if not (p.get(field) or "").strip():
                fails.append("queued item %r: missing %s" % (who, field))
        if p.get("stage") not in stage_ids:
            fails.append("queued item %r: stage=%r is not a cycle stage" % (who, p.get("stage")))

    # A plan item may name the capability it serves. If it does, that capability
    # must exist -- a dangling reference is how the two halves of the page drift
    # apart. And every capability with work queued against it should be findable
    # from that work, which is what makes the document one argument.
    cap_ids = {str(c.get("id")) for c in caps}
    for bucket in ("now", "next"):
        for p in plans.get(bucket, []):
            cid = p.get("capability")
            if cid is not None and str(cid) not in cap_ids:
                fails.append("%s item %r: capability=%r does not exist"
                             % (bucket, p.get("name"), cid))
            if cid is None:
                drifts.append("%s item %r names no capability — the plan list and the "
                              "capabilities table cannot be reconciled by a reader"
                              % (bucket, p.get("name")))

    # A capability whose evidence says it is blocked, with nothing queued against
    # it, is a claim the plan never follows up on.
    served = {str(p.get("capability")) for b in ("now", "next") for p in plans.get(b, [])}
    for c in caps:
        ev = (c.get("evidence") or "").lower()
        if ("blocked" in ev or "no plan" in ev) and str(c.get("id")) not in served:
            drifts.append("capability %s %r reads as blocked but has nothing queued against it"
                          % (c.get("id"), c.get("name")))

    for inv in d.get("invariants", []):
        if inv.get("state") not in VALID_INV:
            fails.append("invariant %r: state=%r is not one of %s"
                         % (inv.get("rule"), inv.get("state"), sorted(VALID_INV)))

    log = d.get("meta", {}).get("changelog", [])
    if log and log[-1].get("version") != d.get("meta", {}).get("plan_version"):
        fails.append("plan_version is %s but the newest changelog entry is %s"
                     % (d["meta"].get("plan_version"), log[-1].get("version")))

    # ---------------------------------------------------------------- page sync
    page_stale = True
    if os.path.exists(OUT):
        fp = hashlib.sha256(open(SRC, "rb").read()).hexdigest()[:12]
        page_stale = ('data-fingerprint="%s"' % fp) not in open(OUT, encoding="utf-8").read()
    if page_stale:
        fails.append("index.html was rendered from a different plan.json — "
                     "re-render the page")

    # ---------------------------------------------------------------- drift
    # Uncommitted work outside the plan directory while the plan sits untouched.
    # This is the
    # everyday case: something got built and the plan was not moved with it.
    dirty = [ln[3:] for ln in git("status", "--porcelain").splitlines()]
    dirty_work = [f for f in dirty if not f.startswith(plan_dir)]
    plan_dirty = any(f == os.path.relpath(SRC, root) for f in dirty)
    if dirty_work and not plan_dirty:
        drifts.append("%d uncommitted file(s) outside %s but the plan is untouched — "
                      "is the plan still describing reality? (%s%s)"
                      % (len(dirty_work), plan_dir, ", ".join(dirty_work[:3]),
                         ", …" if len(dirty_work) > 3 else ""))

    # The last commit that changed something real, versus when the plan last moved.
    last_work = git("log", "-1", "--format=%cI", "--", ".",
                    ":(exclude)%s" % plan_dir.rstrip("/"))
    updated = parse_iso(d.get("meta", {}).get("updated"))
    lw = parse_iso(last_work)
    if lw and updated and lw > updated:
        # Both rendered in UTC. git reports commit times in the committer's local
        # zone with an offset; meta.updated is usually written as Z. The
        # comparison was always correct, but printing 17:26-04:00 next to 21:22Z
        # made a true finding read as nonsense -- and a check nobody believes is
        # a check nobody acts on.
        drifts.append("last substantive commit (%s) is newer than meta.updated (%s) — "
                      "the plan may be behind what landed"
                      % (lw.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%MZ"),
                         updated.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%MZ")))

    # An artifact nobody has touched in a fortnight is decoration.
    if updated:
        age = (datetime.now(timezone.utc) - updated).days
        if age > 14:
            drifts.append("plan.json last updated %d days ago" % age)

    # Work in flight with no written plan is how scope creeps.
    for p in plans.get("now", []):
        if p.get("stage") == "grounded" and not p.get("plan_file"):
            drifts.append("active item %r is grounded but has no plan document yet — "
                          "next stage is 'planned'" % p.get("name"))

    summary = {
        # brief.py consumes this; keep the keys it reads present even when empty.
        "project": d.get("meta", {}).get("project"),
        "cycle": [st.get("id") for st in (d.get("cycle") or L.DEFAULT_CYCLE).get("stages", [])],
        "plan_version": d.get("meta", {}).get("plan_version"),
        "updated": d.get("meta", {}).get("updated"),
        "now": [{"name": p.get("name"), "stage": p.get("stage"),
                 "status": p.get("status")} for p in plans.get("now", [])],
        "next": [{"name": p.get("name"), "stage": p.get("stage"),
                  "has_plan": bool(p.get("plan_file"))} for p in plans.get("next", [])][:4],
        "invariants_not_holding": [
            {"rule": i.get("rule"), "state": i.get("state")}
            for i in d.get("invariants", []) if i.get("state") != "holding"],
        "open_founder_actions": d.get("founder_actions", []),
    }
    return [("FAIL", f) for f in fails], [("DRIFT", f) for f in drifts], summary


def main():
    if not L.has_plan():
        print("  no plan in this project — nothing to check")
        return 0
    fails, drifts, summary = run()

    if "--json" in sys.argv:
        print(json.dumps({"fails": [f for _, f in fails],
                          "drifts": [f for _, f in drifts],
                          "summary": summary}, indent=1))
        return 1 if fails else 0

    for kind, msg in fails:
        print("  FAIL   %s" % msg)
    for kind, msg in drifts:
        print("  DRIFT  %s" % msg)
    if not fails and not drifts:
        print("  plan OK — structure sound, no drift signals")
    elif not fails:
        print("  no structural problems; %d drift signal(s) above" % len(drifts))

    if fails:
        return 1
    return 1 if (drifts and "--strict" in sys.argv) else 0


if __name__ == "__main__":
    sys.exit(main())
