#!/usr/bin/env python3
"""The one command after any change: record what the drawings are, render, gate.

  sync.py            # refresh views' recorded facts from disk, render the page, run the gate
  sync.py --no-views # render and gate only

"Refresh" writes into plan.json, for each view, the spec's current sha256 and
its declared revision -- the two facts the gate later compares. It is the ONLY
writer of those fields, so a hand-typed value can never disagree with the file.
It refuses (exit 2) when a view's spec is missing, because a page that links a
drawing nobody can regenerate is the quiet lie this layer exists to prevent.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_lib as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    if not L.has_plan():
        return 0
    p = L.paths()
    if "--no-views" not in sys.argv:
        d = L.load()
        changed, missing = 0, []
        for v in d.get("views") or []:
            facts = L.view_facts(p["root"], v)
            if not facts:
                missing.append(v.get("spec"))
                continue
            for k, val in facts.items():
                if v.get(k) != val:
                    v[k] = val
                    changed += 1
        if missing:
            print("  sync: view spec(s) missing on disk: %s" % ", ".join(map(str, missing)))
            return 2
        if changed:
            L.save(d, p["root"])
        print("  sync: views refreshed (%d field(s) changed)" % changed)
    for script in ("render.py", "check.py"):
        r = subprocess.run([sys.executable, os.path.join(HERE, script)])
        if r.returncode not in (0, None) and script == "check.py":
            return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
