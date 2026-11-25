#!/usr/bin/env python3
"""The controller's one diff: desired state (the plan) against observed state.

The reconciliation-loop pattern (GitOps, a Kubernetes controller): one function
reads the declared state and what is observed, and returns every difference as
data. The gate (check.py) prints them as FAIL or DRIFT; pause.py writes them
into the handoff; the hooks fire them by event. Nothing here writes, sends or
calls a network: the agent applies tracker fixes through its own connector.

  findings(root, d, event=None) -> [{"check", "level", "message"}]

Checks: config (meta.controller well formed), one_writer (state changed only by
move.py), tracker (Task 6), rule (Task 7, only on the rule's events),
inventory (Task 9). Library only: there is no CLI; read it with check.py --json.
"""
import fnmatch
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_lib as L  # noqa: E402
import tracker  # noqa: E402

EVENTS = ("stop", "session-start", "sync", "pause")  # plus stage:<id> and release:<stage>


_MISSING = object()  # a task absent from a record, distinct from a task with no state (None)


def _f(check, message, level="FAIL"):
    return {"check": check, "level": level, "message": message}


def first_stage(d):
    """The cycle's first stage id ('intent' by default): where a new idea enters."""
    stages = (d.get("cycle") or L.DEFAULT_CYCLE).get("stages") or [{}]
    return stages[0].get("id")


def duplicate_tasks(d):
    """(work id, task name) pairs where one live item lists the same task name twice. Pure.

    controlled() keys tasks by name, so a repeat would hide a state change.
    """
    out = []
    for bucket in ("now", "next"):
        for it in (d.get("plans") or {}).get(bucket) or []:
            wid = L.work_id(it.get("name")) if isinstance(it, dict) else None
            names = [str(t.get("name")) for t in it.get("tasks") or [] if isinstance(t, dict)] if wid else []
            out += [(wid, n) for n in sorted({n for n in names if names.count(n) > 1})]
    return out


FIX = "revert the hand edit, or run move.py --adopt (with the owner's say-so)"  # the one remedy a hand edit has (move.py refuses while edits are pending)


def one_writer_findings(root, d, cfg):
    """Every controlled field that differs from move.py's last recorded write.

    Inputs: root, plan dict, controller config. Output: list of findings.
    Allowed without move.py, because they are planning, not progress: a new
    item in plans.next at the first stage with every task todo; a queued item
    at the first stage removed; any item that rolled into plan/archive/.
    Everything else is a hand edit and FAILs with the exact move.py command.
    """
    if not cfg or not cfg["one_writer"]:
        return []
    st = L.controller_state(root) or {}
    rec = st.get("writes")
    dups = [_f("one_writer", "%s is the work id of more than one live item or release — rename the "
               "duplicate to its own id (--adopt cannot clear this)" % w) for w in L.duplicate_ids(d)]
    dups += [_f("one_writer", "task name %r appears more than once in %s — rename the duplicate "
                "(--adopt cannot clear this)" % (t, w)) for w, t in duplicate_tasks(d)]
    if not isinstance(rec, dict):
        return dups + [_f("one_writer", "meta.controller.one_writer is on but move.py has recorded no write — "
                          "run move.py --adopt once to stamp the current state")]
    if dups:
        return dups
    cur, first = L.controlled(d), first_stage(d)
    archived = L.archived_ids(root)
    out = []
    ritems, citems = rec.get("items") or {}, cur["items"]
    for wid in sorted(set(ritems) | set(citems)):
        a, b = ritems.get(wid), citems.get(wid)
        if a and b:
            if a["bucket"] != b["bucket"]:
                out.append(_f("one_writer", "%s moved from plans.%s to plans.%s by hand — %s"
                              % (wid, a["bucket"], b["bucket"], FIX)))
            if a["stage"] != b["stage"]:
                out.append(_f("one_writer", "stage of %s is %r but move.py last wrote %r — changed by hand; %s"
                              % (wid, b["stage"], a["stage"], FIX)))
            for t in sorted(set(a["tasks"]) | set(b["tasks"])):
                ta, tb = a["tasks"].get(t, _MISSING), b["tasks"].get(t, _MISSING)
                if ta is _MISSING and tb != "todo":
                    out.append(_f("one_writer", "task %r of %s entered at %r by hand — %s"
                                  % (t, wid, tb, FIX)))
                elif tb is _MISSING and ta not in (_MISSING, "todo"):
                    out.append(_f("one_writer", "task %r of %s (%s) was removed by hand — %s" % (t, wid, ta, FIX)))
                elif ta is not _MISSING and tb is not _MISSING and ta != tb:
                    out.append(_f("one_writer", "task %r of %s is %r but move.py last wrote %r — changed by "
                                  "hand; %s" % (t, wid, tb, ta, FIX)))
        elif b:
            if not (b["bucket"] == "next" and b["stage"] == first
                    and all(s == "todo" for s in b["tasks"].values())):
                out.append(_f("one_writer", "%s entered plans.%s at stage %r by hand — %s (an item enters "
                              "plans.next at %r, then moves with move.py)" % (wid, b["bucket"], b["stage"], FIX, first)))
        elif wid not in archived and not (a["bucket"] == "next" and a["stage"] == first):
            out.append(_f("one_writer", "%s left plans.%s by hand (it was at %r) — %s (finish work with "
                          "move.py %s --to done --outcome \"<text>\")" % (wid, a["bucket"], a["stage"], FIX, wid)))
    rrel = rec.get("releases") or {}
    for rid in sorted(set(rrel) | set(cur["releases"])):
        if rid not in rrel:
            out.append(_f("one_writer", "release %s (stage %r) was added by hand — %s"
                          % (rid, cur["releases"][rid], FIX)))
        elif rid not in cur["releases"]:
            out.append(_f("one_writer", "release %s (stage %r) was removed by hand — %s"
                          % (rid, rrel[rid], FIX)))
        elif rrel[rid] != cur["releases"][rid]:
            out.append(_f("one_writer", "stage of %s is %r but move.py last wrote %r — changed by hand; %s"
                          % (rid, cur["releases"][rid], rrel[rid], FIX)))
    return out


_RULE_KEYS = ("name", "on", "if_changed", "then_changed", "why")


def rule_faults(rules, stage_ids):
    """Malformed rules as FAIL strings. Inputs: rules list, cycle stage ids. Output: strings. Side effects: none. Role: gate check.

     A rule is a co-change rule: when any path
    matching if_changed changed since the base, some path matching each
    then_changed pattern must have changed too. Events: stop, session-start, sync,
    pause, stage:<cycle stage id>, release:<stage>."""
    out = []
    for i, r in enumerate(rules):
        where = "meta.controller.rules[%d]" % i
        if not isinstance(r, dict):
            out.append("%s is not an object" % where)
            continue
        where = "rule %r" % r.get("name", i)
        for k in sorted(set(r) - set(_RULE_KEYS)):
            out.append("%s has unknown key %r (known: %s)" % (where, k, ", ".join(_RULE_KEYS)))
        for k in ("name", "why"):
            if not (isinstance(r.get(k), str) and r[k].strip()):
                out.append("%s needs %s (text)" % (where, k))
        for k in ("on", "if_changed", "then_changed"):
            v = r.get(k)
            if not (isinstance(v, list) and v and all(isinstance(x, str) and x for x in v)):
                out.append("%s needs %s (a non-empty list of text)" % (where, k))
        for e in r.get("on") or []:
            if not isinstance(e, str):
                continue
            ok = (e in EVENTS or (e.startswith("stage:") and e[6:] in stage_ids)
                  or (e.startswith("release:") and e[8:].strip()))
            if not ok:
                out.append("%s: event %r is not one of %s, stage:<%s>, release:<stage>"
                           % (where, e, ", ".join(EVENTS), "|".join(stage_ids)))
    return out


ON_BASE = "measured nothing: HEAD is the base branch"  # also listed in gate_hook.WORK_IN_PROGRESS


def _git_ok(root, *args):
    """Run git, returning stdout or None on any failure or timeout. Side effects: reads git only. Role: helper."""
    import subprocess
    try:
        r = subprocess.run(["git", "-c", "core.quotePath=false"] + list(args), cwd=root,
                           capture_output=True, text=True, timeout=10)
    except Exception:
        return None
    return r.stdout.rstrip("\n") if r.returncode == 0 else None


def changed_files(root, base):
    """Paths changed since the merge-base with `base`, plus uncommitted and untracked.

    Inputs: root, base ref. Side effects: reads git only. Role: gate check.
    Returns (set, None) or (None, reason). A missing base, a git failure, or HEAD
    sitting on the base branch is a reason, never an empty set: a rule that
    measured nothing must not pass. The on-base reason starts with ON_BASE.
    Committed changes since the merge-base and the working tree are both
    measured, so a branch with no commit of its own still counts. Paths are
    relative to root (a project in a repository subdirectory sees only its
    own files) and unquoted (non-ASCII names match).
    """
    mb = _git_ok(root, "merge-base", base, "HEAD")
    if not mb:
        return None, "cannot measure changes: no merge-base between %r and HEAD" % base
    head_ref = _git_ok(root, "rev-parse", "--symbolic-full-name", "HEAD")
    base_ref = _git_ok(root, "rev-parse", "--symbolic-full-name", base)
    if head_ref and head_ref == base_ref:
        # On the base branch every commit is "the base", so committed work is
        # invisible. A fresh branch off the base with no commit yet differs by
        # name and is measured from its working tree.
        return None, ("%s %r itself — work on a branch, or set meta.controller.base to a ref "
                      "behind HEAD" % (ON_BASE, base))
    tracked = _git_ok(root, "diff", "--name-only", "--relative", mb)
    untracked = _git_ok(root, "ls-files", "--others", "--exclude-standard")
    if tracked is None or untracked is None:
        return None, "cannot measure changes: git diff failed or timed out"
    return {f for f in (tracked + "\n" + untracked).splitlines() if f}, None


def stage_events(writes, d):
    """Events implied by every stage in the plan that differs from the stamp's (for --adopt).

    Inputs: the stamp's writes record, plan dict. Output: sorted event names. Side effects: none. Role: gate check.
    """
    cur = L.controlled(d)
    old_i, old_r = (writes or {}).get("items") or {}, (writes or {}).get("releases") or {}
    ev = ["stage:%s" % v["stage"] for k, v in sorted(cur["items"].items())
          if (old_i.get(k) or {}).get("stage") != v["stage"]]
    ev += ["release:%s" % s for k, s in sorted(cur["releases"].items()) if old_r.get(k) != s]
    return sorted(set(ev))


def rule_findings(root, cfg, event):
    """FAIL for each rule bound to `event` whose co-change does not hold.

    Inputs: root, controller config, event name. Output: findings. Side effects: reads git only. Role: gate check.
    """
    if not cfg or not event:
        return []
    mine = [r for r in cfg["rules"] if event in (r.get("on") or [])]
    if not mine:
        return []
    files, why = changed_files(root, cfg["base"])
    if why:
        # A session event on the base branch (or with git unreadable) measures
        # nothing but must not block the session: DRIFT. A move, or a missing
        # base ref, is FAIL.
        soft = event in EVENTS and (why.startswith(ON_BASE) or "git diff failed" in why)
        return [_f("rule", "rule %r on %s: %s" % (r["name"], event, why), "DRIFT" if soft else "FAIL")
                for r in mine]
    out = []
    for r in mine:
        hit = sorted(f for f in files if any(fnmatch.fnmatch(f, p) for p in r["if_changed"]))
        if not hit:
            continue
        missing = [p for p in r["then_changed"] if not any(fnmatch.fnmatch(f, p) for f in files)]
        if missing:
            out.append(_f("rule", "rule %r on %s: %s changed but nothing matching %s did (%s)"
                          % (r["name"], event, ", ".join(hit[:3]) + (", …" if len(hit) > 3 else ""),
                             ", ".join(missing), r["why"])))
    return out


def stage_ids(d):
    """The cycle's stage ids. Inputs: plan dict. Output: list. Side effects: none. Role: helper."""
    return [s["id"] for s in (d.get("cycle") or L.DEFAULT_CYCLE)["stages"]]


def tracker_findings(root, d, level):
    """The tracker mirror's state as findings.

    What: malformed config always FAILs; a mirror never reconciled, reconciled
    against other expected rows, or left with differences is `level`.
    Use when: the gate, the handoff and the hooks need the mirror's state.
    Inputs: root, plan dict, level ("FAIL" when meta.controller is set, so drift
    is a red gate; "DRIFT" otherwise, as in 0.18.0). Output: list of findings,
    messages are the 0.18.0 text. Side effects: none (reads the reconcile record).
    Role: gate check.
    """
    tcfg, terr = L.tracker_config(d, root)
    if terr:
        return [_f("tracker", terr)]
    if not tcfg:
        return []
    if tcfg.get("relational"):
        faults = tracker.relational_faults(d, root)
        if faults:
            if level != "FAIL" and len(faults) > 10:
                faults = faults[:10] + ["… and %d more relational problems" % (len(faults) - 10)]
            return [_f("tracker", m, level) for m in faults]
    st = L.tracker_state(root)
    if not st or not st.get("at"):
        return [_f("tracker", "tracker mirror (%s) was never reconciled — fetch its rows and run "
                   "tracker.py diff --actual <file>" % tcfg["kind"], level)]
    if st.get("expected_hash") != tracker.expected_hash(tracker.expected_rows(d, tcfg, root), tcfg):
        return [_f("tracker", "tracker mirror (%s): the rows the plan now expects differ from those last "
                   "reconciled (%s) — fetch the rows and reconcile again" % (tcfg["kind"], st["at"]), level)]
    if st.get("drift"):
        return [_f("tracker", "tracker mirror (%s): the last reconcile (%s) left %s difference(s) — "
                   "apply them and diff again" % (tcfg["kind"], st["at"], st["drift"]), level)]
    return []


def _walk(obj, path):
    """The values at a dot path.

    What: 'a[]' steps into each element of a list, 'a{}' takes a mapping's keys.
    Use when: reading names out of a JSON file. Inputs: parsed JSON, path string.
    Output: list of strings (strings and ints only). Side effects: none.
    Role: helper.
    """
    vals = [obj]
    for part in [p for p in path.split(".") if p]:
        nxt = []
        name, each, keys = part.rstrip("[]{}"), part.endswith("[]"), part.endswith("{}")
        for v in vals:
            v = v.get(name) if (isinstance(v, dict) and name) else v
            if each and isinstance(v, list):
                nxt.extend(v)
            elif keys and isinstance(v, dict):
                nxt.extend(v.keys())
            elif v is not None and not (each or keys):
                nxt.append(v)
        vals = nxt
    return [str(v) for v in vals if isinstance(v, (str, int)) and not isinstance(v, bool)]


def extract(root, src):
    """The entries of one list.

    What: with "json", the values at that path; without, the file's text kept
    whole (coverage is then a whole-word match). An unreadable file, bad JSON or
    an empty extraction is a reason, never an empty list.
    Use when: an inventory or a covering list is read from a file.
    Inputs: root, src = {"file", "json"?}. Output: (entries, None) or (None, reason).
    Side effects: reads one file. Role: helper.
    """
    path = os.path.join(root, src.get("file") or "")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except Exception as exc:
        return None, "cannot read %s (%s)" % (src.get("file"), exc.__class__.__name__)
    if not src.get("json"):
        return [text], None
    try:
        vals = _walk(json.loads(text), src["json"])
    except Exception as exc:
        return None, "cannot parse %s as JSON (%s)" % (src["file"], exc)
    if not vals:
        return None, "%s at %r extracted nothing — the path or the file is wrong" % (src["file"], src["json"])
    return vals, None


def _covered(item, entries, whole_text):
    """Whether item is in the list. Whole text: a whole-word match; else exact entry.

    What: a trailing full stop ends a sentence, not a name, so "a-1." covers a-1
    while "a-1.b", "a-1..env" and "a-1.-x" do not. Use when: comparing an inventory item to
    a covering list. Inputs: item, entries, whole_text flag. Output: bool.
    Side effects: none. Role: helper.
    """
    if whole_text:
        return re.search(r"(?<![\w.-])%s(?![\w-]|\.+[\w-])" % re.escape(item), entries[0]) is not None
    return item in entries


def inventory_findings(root, d):
    """FAIL for every inventory item missing from a list that must cover it.

    What: also FAILs any list that cannot be read, extracts nothing, or is
    malformed; an exemption needs item, list and why.
    Use when: the gate checks a plan that declares an inventory.
    Inputs: root, plan dict. Output: list of findings (none without inventory).
    Side effects: reads the listed files and the tracker reconcile record.
    Role: gate check.
    """
    out = []
    inv = d.get("inventory")
    if inv is None:
        return out
    if not isinstance(inv, dict):
        return [_f("inventory", "inventory is %r — an object of named inventories" % (inv,))]
    for name, spec in sorted(inv.items()):
        who = "inventory %r" % name
        if not (isinstance(spec, dict) and isinstance(spec.get("covered_by"), list) and spec["covered_by"]):
            out.append(_f("inventory", "%s needs covered_by: a non-empty list of lists to check" % who))
            continue
        if "from" in spec:
            src = spec["from"]
            if not (isinstance(src, dict) and src.get("file") and src.get("json")):
                out.append(_f("inventory", "%s: from needs {file, json}: the inventory is a list of names "
                              "read at a JSON path" % who))
                continue
            items, why = extract(root, src)
            if why:
                out.append(_f("inventory", "%s: %s" % (who, why)))
                continue
        else:
            items = spec.get("items")
        if not (isinstance(items, list) and items and all(isinstance(i, str) and i for i in items)):
            out.append(_f("inventory", "%s needs items (a non-empty list of names) or from" % who))
            continue
        labels = {c["list"] for c in spec["covered_by"] if isinstance(c, dict) and isinstance(c.get("list"), str)}
        exempt = {}
        ex_list = spec.get("exempt") or []
        if not isinstance(ex_list, list):
            out.append(_f("inventory", "%s: exempt must be a list of {item, list, why}" % who))
            ex_list = []
        for e in ex_list:
            if not (isinstance(e, dict) and all(isinstance(e.get(k), str) and e[k].strip()
                                                for k in ("item", "list", "why"))):
                out.append(_f("inventory", "%s: an exemption needs item, list and why, all text: %r" % (who, e)))
                continue
            if e["item"] not in items or e["list"] not in labels:
                out.append(_f("inventory", "%s: an exemption names an unknown item or list: %r" % (who, e)))
                continue
            exempt.setdefault(e["list"], set()).add(e["item"])
        for cov in spec["covered_by"]:
            if not isinstance(cov, dict):
                out.append(_f("inventory", "%s: each covered_by entry must be an object {list, file, json?} "
                              "or {list, tracker: true}, not %r" % (who, cov)))
                continue
            label = cov.get("list") if isinstance(cov.get("list"), str) and cov["list"] else None
            if label is None or not (cov.get("tracker") is True or (isinstance(cov.get("file"), str) and cov["file"])):
                out.append(_f("inventory", "%s: each covered_by entry needs a list name and file or tracker: true: %r"
                              % (who, cov)))
                continue
            if cov.get("tracker") is True:
                st = L.tracker_state(root)
                if not st or not isinstance(st.get("actual_keys"), list):
                    out.append(_f("inventory", "%s, list %r: the tracker was never reconciled with "
                                  "keys recorded — run the tracker reconcile" % (who, label)))
                    continue
                entries, whole = [str(k).casefold() for k in st["actual_keys"]], False
                check = [i.casefold() for i in items]
            else:
                entries, why = extract(root, cov)
                if why:
                    out.append(_f("inventory", "%s, list %r: %s" % (who, label, why)))
                    continue
                whole, check = not cov.get("json"), items
            missing = [orig for orig, i in zip(items, check)
                       if orig not in exempt.get(label, set()) and not _covered(i, entries, whole)]
            if missing:
                out.append(_f("inventory", "%s: list %r covers %d of %d — missing %s"
                              % (who, label, len(items) - len(missing), len(items), ", ".join(missing))))
    return out


def findings(root, d, event=None):
    """The whole diff, in check order. Inputs: root, plan dict, event name or None. Pure reads."""
    cfg, err = L.controller_config(d)
    out = [_f("config", err)] if err else one_writer_findings(root, d, cfg)
    if cfg:
        bad = [_f("config", m) for m in rule_faults(cfg["rules"], stage_ids(d))]
        out += bad or rule_findings(root, cfg, event)
    out += tracker_findings(root, d, "FAIL" if (cfg or err) else "DRIFT")
    return out + inventory_findings(root, d)
