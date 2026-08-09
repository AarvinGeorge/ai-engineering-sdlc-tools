#!/usr/bin/env python3
"""Inject plan state into the session automatically. The enforcement half.

A project can write "read the plan first" into its instructions. That is an
instruction, and instructions get skipped -- especially by a fresh session that has not read
far enough to know the rule exists. This makes it happen whether or not
anyone remembers.

Silence is a feature: in a project with no plan file this exits without
emitting anything. A layer that announces itself where it was never invited
is a layer people uninstall.

Two modes, wired to two events:

  --session-start   the state arrives before the first word is typed
  --pre-compact     compaction is when working state is lost; flush first

Output is the hook JSON contract: hookSpecificOutput.additionalContext is
injected into model context. Kept deliberately short -- this runs every
session, and a brief nobody can read is a brief nobody reads.

Never fails loudly: a broken briefing must not block a session. On any
error it emits an empty context and exits 0.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_lib as L  # noqa: E402


def emit(event, text):
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": event, "additionalContext": text},
        "suppressOutput": True,
    }))
    sys.exit(0)


def session_start():
    import check
    fails, drifts, s = check.run()

    lines = ["=== PLAN STATE (injected by plan-layer; the plan JSON is the source) ===",
             "%s · plan v%s · updated %s" % (s.get("project") or "project",
                                             s.get("plan_version"), s.get("updated"))]

    if s.get("now"):
        lines.append("ACTIVE NOW:")
        for p in s["now"]:
            lines.append("  - [%s] %s — %s" % (p.get("stage"), p.get("name"),
                                           (p.get("status") or "")[:160]))
    else:
        lines.append("ACTIVE NOW: nothing")

    if s.get("next"):
        lines.append("NEXT (in order):")
        for p in s["next"]:
            lines.append("  - [%s] %s%s" % (p.get("stage"), p.get("name"),
                                        "" if p.get("has_plan") else "  (NO PLAN WRITTEN)"))

    bad = s.get("invariants_not_holding") or []
    if bad:
        lines.append("INVARIANTS NOT HOLDING:")
        for i in bad:
            lines.append("  - %s: %s" % (i.get("rule"), i.get("state")))

    if fails:
        lines.append("PLAN GATE FAILING — fix before reporting status:")
        for _, m in fails:
            lines.append("  - %s" % m)
    if drifts:
        lines.append("DRIFT SIGNALS:")
        for _, m in drifts:
            lines.append("  - %s" % m)

    lines.append("Cycle: %s. Move the item's stage in the plan as it advances, and "
                 "finish the turn by re-rendering and running the check "
                 "(see the plan-layer skill)." % " -> ".join(s.get("cycle") or []))
    emit("SessionStart", "\n".join(lines))


def pre_compact():
    import check
    _, _, s = check.run()
    active = "; ".join("%s [%s]" % (p.get("name"), p.get("stage")) for p in s.get("now") or []) \
        or "nothing recorded as active"
    emit("PreCompact",
         "=== FLUSH STATE BEFORE COMPACTING ===\n"
         "Context is about to be summarized, which is where working state gets lost.\n"
         "Before continuing, write anything learned this session into the plan JSON — "
         "stage changes, new next-items, invariants that moved, facts measured — then run "
         "the render script. Log any locked decision in the project's decision log.\n"
         "The plan currently says active: %s (last updated %s). If that is already stale, "
         "it is about to become the only memory that survives." % (active, s.get("updated")))


def main():
    try:
        # Hooks receive JSON on stdin; nothing here needs it, but it must be
        # drained so the writing end never blocks on a full pipe.
        if not sys.stdin.isatty():
            sys.stdin.read()
    except Exception:
        pass

    # Silent when the project has not opted in. No output at all.
    if not L.has_plan():
        sys.exit(0)

    try:
        if "--pre-compact" in sys.argv:
            pre_compact()
        else:
            session_start()
    except Exception as exc:
        # A briefing that cannot be produced must never block the session.
        emit("SessionStart", "plan-layer brief unavailable (%s). Read the plan JSON "
                             "manually before starting work." % exc)


if __name__ == "__main__":
    main()
