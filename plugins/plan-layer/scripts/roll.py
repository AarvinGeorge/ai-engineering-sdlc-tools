#!/usr/bin/env python3
"""Roll aged records off the live plan into plan/archive/, so the page shows this month.

A planning page that carries every completed item and every changelog entry
since the project began stops being read. This moves the history, in full and
machine-readable, out of the live file and leaves a count behind: the last
keep_done completed items, the last keep_log changelog entries and the first
keep_next queued items stay (plus one queued item per capability, so the gate
never reads "blocked with nothing queued" because of a roll). Everything else
the page shows -- the active item, capabilities, parked questions, invariants,
edge cases, glossary, facts -- is live state, not history, and is untouched.

Nothing is deleted. Archive files are append-only and de-duplicated, so
running this twice is safe. Overrides per project in .plan-layer.json:
  {"roll": {"keep_done": 8, "keep_log": 10, "keep_next": 8}}

  roll.py            # move, then print what moved and the new size
  roll.py --dry-run  # print only
Then render, run the gate, republish.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_lib as L  # noqa: E402


def _append(path, items):
    if not items:
        return 0
    have = json.load(open(path, encoding="utf-8")) if os.path.isfile(path) else []
    keys = {json.dumps(x, sort_keys=True, ensure_ascii=False) for x in have}
    new = [x for x in items if json.dumps(x, sort_keys=True, ensure_ascii=False) not in keys]
    L.atomic_write(path, json.dumps(have + new, indent=1, ensure_ascii=False) + "\n")
    return len(new)


def main():
    if not L.has_plan():
        return 0
    dry = "--dry-run" in sys.argv
    p = L.paths()
    cfg = L.roll_config(p["root"])
    d = L.load()
    before = os.path.getsize(p["src"])
    r = L.rollable(d, cfg)
    print("%s done: %d  changelog: %d  queued-to-backlog: %d"
          % ("would move" if dry else "moving", len(r["done"]), len(r["changelog"]), len(r["next"])))
    if dry or not (r["done"] or r["changelog"] or r["next"]):
        return 0
    adir = os.path.join(p["dir"], L.ARCHIVE_DIRNAME)
    os.makedirs(adir, exist_ok=True)
    n1 = _append(os.path.join(adir, "done.json"), r["done"])
    n2 = _append(os.path.join(adir, "changelog.json"), r["changelog"])
    n3 = _append(os.path.join(adir, "backlog.json"), r["next"])
    d["plans"]["done"] = d["plans"]["done"][-cfg["keep_done"]:]
    d["meta"]["changelog"] = d["meta"]["changelog"][-cfg["keep_log"]:]
    d["plans"]["next"] = r["keep_next"]
    L.save(d, p["root"])
    print("archived new records: done %d, changelog %d, backlog %d" % (n1, n2, n3))
    print("%s: %d -> %d bytes" % (os.path.basename(p["src"]), before, os.path.getsize(p["src"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
