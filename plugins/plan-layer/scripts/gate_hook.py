#!/usr/bin/env python3
"""Stop hook: refuse to end a turn on a structurally broken plan.

The loop said "finish every substantive turn by re-rendering and running the
gate". That is an instruction, and the human ended up being the one who
noticed when it was skipped. This makes it happen instead.

WHAT IT BLOCKS ON, and what it deliberately does not:

  FAIL   blocks. These are objective and always worth fixing before the turn
         ends -- a capability claiming progress with no evidence, a dangling
         reference, a page rendered from different data, an alarm with no
         detail.

  DRIFT  does NOT block. Every drift signal fires routinely during ordinary
         work ("uncommitted files outside plan/", "last commit newer than the
         plan"), and a hook that interrupts every turn is a hook someone
         disables. Drift is reported at session start instead.

Loop safety matters more than the feature: a Stop hook that blocks forever
makes a session unusable. Three guards -- honour `stop_hook_active` when the
harness sets it, never block twice for the same failures in the same session,
and fail open on any internal error.
"""
import hashlib
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_lib as L  # noqa: E402



# Two kinds of drift, and only one belongs at the end of a turn.
#
# WORK-IN-PROGRESS signals fire constantly and correctly while someone is
# mid-task: files edited but not committed, a commit newer than the plan. They
# are useful at session start, as a summary of where things were left. Shown
# after every turn they would be pure noise, and a notice that is always there
# is one nobody reads.
#
# STALENESS signals mean the page has stopped describing reality. Those are the
# ones that went unnoticed for days at a time, and they are what the human asked
# to stop experiencing. They surface immediately, without blocking.
WORK_IN_PROGRESS = (
    "uncommitted file",
    "is newer than meta.updated",
)


def _is_staleness(message):
    return not any(marker in message for marker in WORK_IN_PROGRESS)


def _seen_path(session, digest, project):
    """One marker per session + project + set-of-failures.

    The project is part of the key because a session id may be absent, and
    without it two different repositories with the same failure would suppress
    each other -- which is the kind of silence that looks like a passing gate.
    """
    safe = "".join(c for c in str(session) if c.isalnum())[:40] or "nosession"
    proj = hashlib.sha256(os.path.abspath(project).encode()).hexdigest()[:8]
    return os.path.join(tempfile.gettempdir(),
                        "plan-layer-gate-%s-%s-%s" % (safe, proj, digest))


def main():
    try:
        raw = sys.stdin.read() if not sys.stdin.isatty() else "{}"
        payload = json.loads(raw or "{}")
    except Exception:
        payload = {}

    # The harness sets this when it is already re-running us after a block.
    if payload.get("stop_hook_active"):
        return 0

    if not L.has_plan():
        return 0

    try:
        import check
        fails, drifts, _summary = check.run()
    except Exception:
        # A broken gate must never trap a session.
        return 0

    stale = [m for _kind, m in drifts if _is_staleness(m)]

    if not fails:
        # Nothing is broken, but the page may have stopped matching reality.
        # Say so where the human will see it, rather than saving it for the next
        # session -- which is how the same three things went unnoticed for days.
        if stale:
            print(json.dumps({
                "systemMessage": (
                    "Plan drift (%d): the page may no longer match reality.\n  "
                    % len(stale)) + "\n  ".join(stale[:6]),
            }))
        return 0

    messages = [m for _kind, m in fails]
    digest = hashlib.sha256("\n".join(sorted(messages)).encode()).hexdigest()[:12]
    marker = _seen_path(payload.get("session_id"), digest, L.paths()["root"])
    if os.path.exists(marker):
        # Same failures already raised once this session. Saying it again would
        # be nagging, and nagging is how a useful signal gets switched off.
        return 0
    try:
        open(marker, "w").close()
    except OSError:
        pass

    print(json.dumps({
        "decision": "block",
        "reason": (
            "The plan gate is failing, so this turn is not finished.\n\n  "
            + "\n  ".join(messages)
            + "\n\nFix the plan (and re-render if the page is stale), then finish. "
              "If a failure is wrong, correct the check rather than working around it."
        ),
        "systemMessage": (
            ("Plan gate: %d failure(s)" % len(messages))
            + (", %d drift signal(s)" % len(stale) if stale else "")
        ),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
