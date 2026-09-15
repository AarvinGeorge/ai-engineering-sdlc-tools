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
  check.py --verify  # run the plan's assertions against the real system
                     # (explicit only — never run from a hook)
"""
import hashlib
import io
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_lib as L  # noqa: E402

VALID_BUILD = {"done", "active", "partial", "not-started"}
VALID_PLAN = {"planned", "partial", "none"}
VALID_INV = {"holding", "at risk", "broken"}
VALID_TASK = {"done", "active", "todo", "blocked"}
# The keys a task already owns. A declared column may not take one of them:
# the column value would land on the step's own name, state or note.
RESERVED_TASK_KEYS = ("name", "state", "note")






def column_faults(who, p):
    """A malformed `task_columns` block, in words.

    A checklist rendered as a table is only readable if the columns are, so a
    declaration that cannot produce a table is a hard failure rather than a
    silently narrower table.
    """
    cols = p.get("task_columns")
    if cols is None:
        return []
    out = []
    if not isinstance(cols, list):
        return ["%r: task_columns must be a list of {key, label}, not %s"
                % (who, type(cols).__name__)]
    seen = set()
    for i, c in enumerate(cols, 1):
        where = "%r: task_columns[%d]" % (who, i)
        if not isinstance(c, dict):
            out.append("%s is not an object with key and label" % where)
            continue
        key, label = c.get("key"), c.get("label")
        if not key:
            out.append("%s has no key" % where)
        if not label:
            out.append("%s has no label" % where)
        if key in RESERVED_TASK_KEYS:
            out.append("%s uses %r, which is a reserved task key (%s). Its value "
                       "would be read as the step's own %s"
                       % (where, key, ", ".join(RESERVED_TASK_KEYS), key))
        elif key in seen:
            out.append("%s repeats the duplicate key %r" % (where, key))
        if key:
            seen.add(key)
    return out


def empty_cells(who, p):
    """Declared columns an unfinished step never filled in.

    The columns exist so somebody can execute the step from the page. A blank
    cell on a step still to run means the page cannot be worked from, which is
    the whole reason for declaring them. A finished step is exempt: once it has
    passed, its instructions are history.
    """
    cols = p.get("task_columns")
    if not isinstance(cols, list):
        return []
    keys = [c.get("key") for c in cols
            if isinstance(c, dict) and c.get("key") and c.get("key") not in RESERVED_TASK_KEYS]
    out = []
    for t in p.get("tasks") or []:
        if t.get("state") not in ("active", "todo"):
            continue
        missing = [k for k in keys if not str(t.get(k) or "").strip()]
        if missing:
            out.append("%r: step %r leaves %s empty, so the step cannot be run "
                       "from the page"
                       % (who, t.get("name", "?"), ", ".join(repr(k) for k in missing)))
    return out


def parse_iso(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def verify(root=None):
    """Run the plan's own assertions against the real system.

    This is the one thing a structural gate cannot do on its own: decide
    whether a claim is TRUE. The plan states how each claim is checked, and
    this runs those checks and compares.

    SECURITY, and the reason this is never automatic: assertions are shell
    commands read out of a JSON file in the repository. Running them on session
    start would mean cloning a repository executes its author's commands. So
    they run only when a human types `check.py --verify`, never from a hook,
    and never as part of the ordinary gate.
    """
    import subprocess as sp
    import tempfile
    P = L.paths(root)
    d = json.load(open(P["src"], encoding="utf-8"))
    items = d.get("assertions") or []
    if not items:
        print("  no assertions declared — nothing to verify against the real system")
        return 0, 0

    # One gather, many checks.
    #
    # Assertions that each open their own connection are slow, and worse: eight
    # back-to-back SSH connections tripped a host's `ufw limit 22/tcp` rule and
    # locked this machine out of its own server. The claims were all true; the
    # verification method was the problem, and an assertion that ERRORS looks
    # exactly like an assertion that FAILS.
    #
    # So a plan may declare `assertions_setup`: one command, run once, whose
    # stdout is written to a file. Assertions then read that file via
    # $PLAN_FACTS instead of reaching out again.
    env = dict(os.environ)
    facts_path = None
    setup = d.get("assertions_setup")
    if setup:
        try:
            r = sp.run(["bash", "-lc", setup], cwd=P["root"], capture_output=True,
                       text=True, timeout=180)
            if r.returncode != 0:
                print("  SETUP FAILED (%s) — every assertion below would report a false "
                      "mismatch, so nothing was run.\n  %s"
                      % (r.returncode, (r.stderr or "").strip()[:200]))
                return 0, 1
            fh = tempfile.NamedTemporaryFile("w", suffix=".facts", delete=False)
            fh.write(r.stdout)
            fh.close()
            facts_path = fh.name
            env["PLAN_FACTS"] = facts_path
            print("  setup: gathered %d lines of facts in one call\n"
                  % len(r.stdout.splitlines()))
        except Exception as exc:
            print("  SETUP ERRORED (%s) — nothing was run." % exc)
            return 0, 1

    ok = bad = 0
    for a in items:
        claim, cmd = a.get("claim", "?"), a.get("run")
        if not cmd:
            print("  SKIP    %s — no `run` command" % claim)
            continue
        try:
            r = sp.run(["bash", "-lc", cmd], cwd=P["root"], capture_output=True,
                       text=True, timeout=a.get("timeout", 60), env=env)
            got = r.stdout.strip()
            # An empty result from a non-zero exit is the command failing, not
            # the claim being false. Saying so is the difference between a
            # useful signal and a false alarm.
            if not got and r.returncode != 0:
                print("  ERRORED %-46s command exited %d: %s"
                      % (claim, r.returncode, (r.stderr or "").strip()[:60]))
                bad += 1
                continue
        except Exception as exc:
            print("  ERROR   %-46s %s" % (claim, exc))
            bad += 1
            continue
        exp = str(a.get("expect", "")).strip()
        hit = re.search(exp, got) is not None if a.get("match") == "regex" else got == exp
        if hit:
            ok += 1
            print("  MATCH   %-46s %s" % (claim, got[:40]))
        else:
            bad += 1
            print("  MISMATCH %-45s expected=%r actual=%r" % (claim, exp, got[:80]))
    if facts_path:
        try:
            os.unlink(facts_path)
        except Exception:
            pass
    print("\n  %d matched, %d mismatched, %d declared" % (ok, bad, len(items)))
    if bad:
        print("  note: an assertion that ERRORED is a broken check, not a broken claim.")
    return ok, bad


# Words that assert work has NOT happened yet. Harmless in a queued item;
# a contradiction in one whose own tasks are recorded as finished.
NOT_YET = re.compile(
    r"\b(waiting for (its|the|a) first|has never (run|been)|not (yet )?(built|started|run)|"
    r"yet to be (built|run|tested)|about to (build|start)|no (adapter|path) (exists|yet))\b",
    re.I)

# Cross-references only someone with the page open can resolve.
BARE_REF = re.compile(r"(?<![\w-])([PE]\d{1,2})(?![\w-])")

# Shorthand that assumes a conversation the reader did not have.
INSIDER = re.compile(
    r"\b(as discussed|as we said|you know the one|per our chat|the usual|"
    r"is a Tuesday|obviously)\b", re.I)


def _prose_fields(d):
    """Every human-facing string on the page, with a label for each."""
    out = []
    for k, v in (d.get("orientation") or {}).items():
        out.append(("orientation.%s" % k, v))
    for k, v in (d.get("contract") or {}).items():
        out.append(("contract.%s" % k, v))
    for c in d.get("capabilities") or []:
        who = "capability %s" % c.get("id")
        for f in ("what", "evidence"):
            if c.get(f):
                out.append(("%s %s" % (who, f), c[f]))
    plans = d.get("plans") or {}
    for p in plans.get("now") or []:
        if p.get("status"):
            out.append(("active item %r" % p.get("name"), p["status"]))
    for p in plans.get("next") or []:
        for f in ("why", "unblocks"):
            if p.get(f):
                out.append(("queued item %r %s" % (p.get("name"), f), p[f]))
    for q in d.get("parked") or []:
        if q.get("note"):
            out.append(("parked %s" % q.get("id"), q["note"]))
    for e in d.get("edge_cases") or []:
        for f in ("case", "mitigation"):
            if e.get(f):
                out.append(("edge case %s %s" % (e.get("id"), f), e[f]))
    for i in d.get("invariants") or []:
        if i.get("detail"):
            out.append(("invariant %r" % i.get("rule"), i["detail"]))
    return out


def check_contradictions(d):
    """Claims the plan's own state disproves.

    Not a judgement about the world -- purely internal. If the page says a
    thing has not happened while the same page records it as done, one of the
    two is wrong and a human has to look.
    """
    fails = []
    plans = d.get("plans") or {}

    for p in plans.get("now") or []:
        who = p.get("name") or "active item"
        tasks = p.get("tasks") or []
        done = [t for t in tasks if t.get("state") == "done"]
        status = p.get("status") or ""
        m = NOT_YET.search(status)
        if m and done:
            fails.append(
                "active item %r says %r but %d of its own tasks are recorded done — "
                "the page contradicts itself"
                % (who, m.group(0), len(done)))

    # A capability cannot be untouched if finished work claims to have served it.
    served_by_done = set()
    for p in plans.get("done") or []:
        if p.get("capability") is not None:
            served_by_done.add(str(p["capability"]))
    for c in d.get("capabilities") or []:
        if str(c.get("id")) in served_by_done and c.get("build") == "not-started":
            fails.append(
                "capability %s %r is 'not-started', but completed work is filed against it"
                % (c.get("id"), c.get("name")))

    # An active item's capability should not read as untouched either.
    active_caps = {str(p["capability"]) for p in (plans.get("now") or [])
                   if p.get("capability") is not None}
    for c in d.get("capabilities") or []:
        if str(c.get("id")) in active_caps and c.get("build") == "not-started":
            fails.append(
                "capability %s %r is 'not-started' while an active item works on it"
                % (c.get("id"), c.get("name")))
    return fails


def check_readability(d):
    """The property this page exists for.

    A stranger should be able to read it and understand the project. That is
    not decoration -- it is the stated purpose, and prose drifts toward
    shorthand every single time someone who already knows the answer writes it.
    """
    fails, drifts = [], []
    terms = {g.get("term", "").lower() for g in (d.get("glossary") or [])}
    ids = {str(q.get("id")) for q in (d.get("parked") or [])}
    ids |= {str(e.get("id")) for e in (d.get("edge_cases") or [])}

    for label, text in _prose_fields(d):
        m = INSIDER.search(text)
        if m:
            fails.append("%s uses %r — shorthand a new reader cannot resolve" % (label, m.group(0)))

        for ref in set(BARE_REF.findall(text)):
            if ref in ids and ref not in label:
                drifts.append(
                    "%s refers to %s without saying what it is — a reader has to go hunting"
                    % (label, ref))

        # Sentences long enough that a reader loses the thread.
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            n = len(sentence.split())
            if n > 55:
                drifts.append("%s has a %d-word sentence — hard to follow in one pass"
                              % (label, n))
                break

    # Capitalised multi-word terms used in prose with no glossary entry.
    if terms:
        JARGON = re.compile(r"\b([A-Z][a-z]+(?:[ -][A-Z][a-z]+){1,2})\b")
        seen = {}
        for label, text in _prose_fields(d):
            for cand in JARGON.findall(text):
                seen.setdefault(cand.lower(), label)
        for cand, label in sorted(seen.items()):
            if cand in terms:
                continue
            if len(cand.split()) < 2:
                continue
            drifts.append("%s uses %r, which is not in the glossary" % (label, cand.title()))
    return fails, drifts


def check_figures(root, d):
    """A figure that asks for a fact nobody defined renders a question mark.

    Figures read numbers and statuses from the plan so the picture cannot drift
    from the words -- that is the whole point of the facts block. But a typo, or
    a fact removed while a figure still wants it, degrades silently into "?" in
    a drawing nobody re-reads. Cheap to catch, invisible otherwise.
    """
    drifts = []
    fig = os.path.join(os.path.dirname(L.paths(root)["src"]), "figures.py")
    if not os.path.exists(fig):
        return drifts
    try:
        src = io.open(fig, encoding="utf-8").read()
    except OSError:
        return drifts
    facts = set((d.get("facts") or {}).keys())
    wanted = set(re.findall(r'F\.get\(\s*["\']([a-z_]+)["\']', src))
    for k in sorted(wanted - facts):
        drifts.append("a figure reads fact %r, which is not in the plan — it will draw '?'" % k)
    return drifts


def check_dependencies(d):
    """"This waits on that" must be data, not prose.

    A dependency written only in a plan document, or only in the agent's
    reasoning, cannot be checked by anything. That is exactly how an item stayed
    marked 'active' for three days while the work it depended on sat unstarted
    at the bottom of the queue -- the human caught it, the gate could not,
    because the file had nowhere to record the link.

    An item may declare `blocked_by: ["name of another item"]`.
    """
    fails, drifts = [], []
    plans = d.get("plans") or {}
    by_name = {}
    for bucket in ("now", "next", "done"):
        for p in plans.get(bucket) or []:
            if p.get("name"):
                by_name[p["name"]] = (bucket, p)

    for bucket in ("now", "next"):
        for p in plans.get(bucket) or []:
            who = p.get("name") or "item"
            for dep in p.get("blocked_by") or []:
                if dep not in by_name:
                    fails.append("item %r says it waits on %r, which is not on the plan at all"
                                 % (who, dep))
                    continue
                dep_bucket, dep_item = by_name[dep]
                if dep_bucket == "done":
                    drifts.append("item %r still says it waits on %r, which is finished"
                                  % (who, dep))
                    continue
                # The thing it waits on must not look less real than it does.
                if bucket == "now" and dep_bucket == "next":
                    unfinished = [t for t in (p.get("tasks") or [])
                                  if t.get("state") in ("active", "todo")]
                    if unfinished:
                        fails.append(
                            "item %r is active with work outstanding, but waits on %r which is "
                            "only queued — one of the two is in the wrong place"
                            % (who, dep))
    return fails, drifts


def check_stalled(d):
    """An active item where nothing can actually move.

    If every task that is not done is blocked, the item is not being worked on;
    it is waiting. Saying 'active' then is how a page looks busy while nothing
    happens.
    """
    drifts = []
    for p in (d.get("plans") or {}).get("now") or []:
        tasks = p.get("tasks") or []
        if not tasks:
            continue
        movable = [t for t in tasks if t.get("state") in ("active", "todo")]
        blocked = [t for t in tasks if t.get("state") == "blocked"]
        if blocked and not movable:
            drifts.append(
                "active item %r has nothing that can move — every unfinished task is blocked. "
                "Either it is waiting rather than active, or a blocker has cleared"
                % (p.get("name") or "item"))
    return drifts


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
        # A mistyped state renders as 'todo', so a finished task would silently
        # read as outstanding -- the page would understate progress and nobody
        # would know why.
        tasks = p.get("tasks") or []
        for t in tasks:
            if t.get("state") not in VALID_TASK:
                fails.append("active item %r: task %r has state=%r, not one of %s"
                             % (who, t.get("name", "?"), t.get("state"),
                                ", ".join(sorted(VALID_TASK))))
        fails.extend(column_faults(who, p))
        drifts.extend(empty_cells(who, p))
        if tasks and all(t.get("state") == "done" for t in tasks) \
                and p.get("stage") not in {"verified", "recorded"}:
            drifts.append("active item %r has every task done but sits at stage %r — "
                          "either it is finished, or the task list is behind"
                          % (who, p.get("stage")))

    # One thing in flight, with its own checklist, is what lets the page answer
    # "what is happening right now" in a glance. A project that genuinely runs
    # several streams says so in the file rather than by accident.
    if len(plans.get("now", [])) > 1 and not d.get("meta", {}).get("allow_multiple_active"):
        fails.append("plans.now holds more than one item (%s) — a reader cannot tell which "
                     "one is the work. Move the others to plans.next, or set "
                     "meta.allow_multiple_active" % ", ".join(
                         repr(p.get("name")) for p in plans.get("now", [])))

    for p in plans.get("next", []):
        who = p.get("name") or "queued item"
        for field in ("name", "why", "unblocks"):
            if not (p.get(field) or "").strip():
                fails.append("queued item %r: missing %s" % (who, field))
        if p.get("stage") not in stage_ids:
            fails.append("queued item %r: stage=%r is not a cycle stage" % (who, p.get("stage")))
        fails.extend(column_faults(who, p))
        drifts.extend(empty_cells(who, p))

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

    ids = [c.get("id") for c in caps]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        fails.append("duplicate capability ids: %s — every reference to them is ambiguous"
                     % sorted(dupes))

    # Two items pointing at one plan document means one of them is mislabelled.
    files = [p.get("plan_file") for b in ("now", "next")
             for p in plans.get(b, []) if p.get("plan_file")]
    for f in {x for x in files if files.count(x) > 1}:
        fails.append("plan_file %r is claimed by more than one item" % f)

    # 'recorded' is the end of the cycle; an item sitting there is finished and
    # belongs in plans.done, or the stage is wrong.
    for p in plans.get("now", []):
        if p.get("stage") == "recorded":
            drifts.append("active item %r is at stage 'recorded' — finished work belongs in "
                          "plans.done" % p.get("name"))

    # A broken invariant with no detail is an alarm with no information.
    for i in d.get("invariants", []):
        if i.get("state") != "holding" and not (i.get("detail") or "").strip():
            fails.append("invariant %r is %r with no detail — an alarm nobody can act on"
                         % (i.get("rule"), i.get("state")))

    # Parked means deferred, not dropped. Without a trigger it is dropped.
    # An edge case with no status is a note; with a status it is tracked work.
    for c in d.get("edge_cases", []):
        if c.get("status") not in ("open", "mitigated", "accepted"):
            fails.append("edge case %r: status=%r must be open, mitigated or accepted"
                         % (c.get("id"), c.get("status")))
        if c.get("status") == "accepted" and not (c.get("mitigation") or "").strip():
            fails.append("edge case %r is 'accepted' with no reasoning — accepting a hazard "
                         "silently is how it stops being a decision" % c.get("id"))

    for q in d.get("parked", []):
        if not (q.get("trigger") or "").strip():
            fails.append("parked question %r has no trigger — parked without one is dropped"
                         % q.get("id"))

    # A timestamp from the future is a clock error, and every age computed from
    # it will be wrong in the reassuring direction.
    upd = parse_iso(d.get("meta", {}).get("updated"))
    if d.get("meta", {}).get("updated") and not upd:
        fails.append("meta.updated %r is not an ISO-8601 timestamp"
                     % d["meta"]["updated"])
    elif upd and upd > datetime.now(timezone.utc):
        fails.append("meta.updated is in the future (%s) — the clock was guessed, not read"
                     % upd.isoformat())

    # Assertions exist to be run. Declared and never run is worse than none,
    # because the page looks verified.
    if d.get("assertions") and not d.get("meta", {}).get("assertions_verified"):
        drifts.append("%d assertions declared but never recorded as run — "
                      "`check.py --verify`" % len(d["assertions"]))
    av = parse_iso(d.get("meta", {}).get("assertions_verified"))
    if av and (datetime.now(timezone.utc) - av).days > 7:
        drifts.append("assertions last verified %d days ago"
                      % (datetime.now(timezone.utc) - av).days)

    # An invariant that alarms about work already finished. Found by hand on
    # 2026-08-10: "off-machine backup at risk -- the archive misses the email
    # layer" was still showing after the capture had put that layer in three
    # places. A stale alarm teaches people to ignore alarms.
    done_words = set()
    for p_ in plans.get("done", []):
        done_words.update(w.strip(".,:;()").lower()
                          for w in (p_.get("name", "") + " " + p_.get("outcome", "")).split()
                          if len(w) > 5)
    for i in d.get("invariants", []):
        if i.get("state") == "holding":
            continue
        detail = set(w.strip(".,:;()").lower() for w in (i.get("detail") or "").split())
        shared = detail & done_words
        if len(shared) >= 3:
            drifts.append("invariant %r is %r, but its detail overlaps completed work (%s) — "
                          "check whether the reason still stands"
                          % (i.get("rule"), i.get("state"), ", ".join(sorted(shared)[:4])))

    # A finished plan is the historical record, and an entry with no dates and
    # no result is a name in a list. Both are drift rather than failure: an item
    # is MOVED into done and condensed afterwards, so the gap is usually minutes
    # old, and a hard failure there would block the very turn that moved it.
    for p in plans.get("done", []):
        who = p.get("name") or "a finished plan"
        if not str(p.get("period") or "").strip():
            drifts.append("finished plan %r has no period — an undated record cannot be "
                          "read in order" % who)
        # `status` is the field name an item arrives with; the page renders it in
        # the same slot as `outcome`, so it counts.
        if not str(p.get("outcome") or p.get("status") or "").strip():
            drifts.append("finished plan %r says nothing about what it produced — add an "
                          "outcome" % who)

    # Two version fields that disagree mean one of them is wrong, and only one
    # of them is read anywhere.
    legacy = d.get("meta", {}).get("version")
    if legacy and legacy != d.get("meta", {}).get("plan_version"):
        drifts.append("meta.version is %s but plan_version is %s — meta.version is legacy and "
                      "nothing reads it; delete it or keep the two the same"
                      % (legacy, d.get("meta", {}).get("plan_version")))

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
    # A tolerance, because plan and commit are usually written in the same minute
    # and a 12-second gap is not drift. Without it the signal reports "00:44Z is
    # newer than 00:44Z", which is true to the second and reads as nonsense --
    # the same way the local-vs-UTC display bug did. A check people learn to
    # dismiss is worse than no check.
    if lw and updated and (lw - updated).total_seconds() > 120:
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
    # Staleness detection (0.8.0). Structure was never the thing that rotted;
    # the page quietly disagreeing with itself was.
    drifts.extend(check_figures(root, d))
    df, dd = check_dependencies(d)
    fails.extend(df)
    drifts.extend(dd)
    drifts.extend(check_stalled(d))
    fails.extend(check_contradictions(d))
    rf, rd = check_readability(d)
    fails.extend(rf)
    drifts.extend(rd)

    return [("FAIL", f) for f in fails], [("DRIFT", f) for f in drifts], summary


def main():
    if not L.has_plan():
        print("  no plan in this project — nothing to check")
        return 0

    if "--verify" in sys.argv:
        # Explicit only. Never wired to a hook: see verify()'s docstring.
        _, bad = verify()
        return 1 if bad else 0

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
