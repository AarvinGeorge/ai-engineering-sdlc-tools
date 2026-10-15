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

Since 0.16.0 sync.py rolls automatically (lossless, the same function), so
running this by hand is only needed for --dry-run or after `sync.py --no-roll`.

  roll.py            # move, then print what moved and the new size
  roll.py --dry-run  # print only
Then render, run the gate, republish.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_lib as L  # noqa: E402


def main():
    if not L.has_plan():
        return 0
    dry = "--dry-run" in sys.argv
    p = L.paths()
    if dry:
        r = L.rollable(L.load(), L.roll_config(p["root"]))
        print("would move done: %d  changelog: %d  queued-to-backlog: %d"
              % (len(r["done"]), len(r["changelog"]), len(r["next"])))
        return 0
    r = L.roll(p["root"])
    print("moving done: %d  changelog: %d  queued-to-backlog: %d" % (r["done"], r["changelog"], r["next"]))
    if "new" in r:
        print("archived new records: done %d, changelog %d, backlog %d" % r["new"])
        print("%s: %d -> %d bytes" % (os.path.basename(p["src"]), r["before"], r["after"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
