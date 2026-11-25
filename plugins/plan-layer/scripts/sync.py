#!/usr/bin/env python3
"""The one command after any change: record what the drawings are, render, gate.

  sync.py                          # refresh views' recorded facts from disk, render the page, run the gate
  sync.py --no-views               # skip the view refresh
  sync.py --no-roll                # do not roll aged records into plan/archive/ (0.16.0)
  sync.py --tracker [--actual <f>] # ALSO mirror the plan into meta.tracker's tracker (0.18.0): print the
                                   # expected rows and the next step, or, with --actual <file> of rows the agent
                                   # fetched through the tracker's connector, the exact fixes (exit 1 on drift,
                                   # 2 on unreadable input). Runs after the render and before the gate, so the
                                   # gate sees the reconcile it just recorded.
  sync.py --live-revision <sha>    # ALSO record the commit that is running (facts.live_revision), then the above.
                                   # For a deploy script's last step: the value should be read off the running
                                   # system (a build stamp, an image label), never recalled.

"Refresh" writes into plan.json, for each view, the spec's current sha256 and
its declared revision -- the two facts the gate later compares. It is the ONLY
writer of those fields, so a hand-typed value can never disagree with the file.
It refuses (exit 2) when a view's spec is missing, because a page that links a
drawing nobody can regenerate is the quiet lie this layer exists to prevent.

Rolling (0.16.0): when records have aged off the front page, sync moves them
into plan/archive/ in full (plan_lib.roll -- the same function roll.py runs, so
there is one rule) and prints what moved. Lossless; --no-roll opts out. A plan
in light mode (meta.mode = "light") is never rolled: it has no archive. Views
are opt-in in both modes: once declared they are refreshed and checked alike.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_lib as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def tracker_step():
    """The --tracker leg: summary and next step, or the diff against --actual. Returns its exit code.

    Why here: sync is "the one command after any change", so the mirror is
    reconciled by the same command, with the same rule as tracker.py.
    """
    import tracker
    d = L.load()
    cfg, err = L.tracker_config(d, L.paths()["root"])
    if err or cfg is None:
        print("  sync: tracker: %s" % (err or "--tracker given but meta.tracker is not set"))
        return 2
    if "--actual" in sys.argv:
        i = sys.argv.index("--actual")
        if i + 1 >= len(sys.argv):
            print("  sync: tracker: --actual needs a file")
            return 2
        print("  sync: tracker reconcile against %s" % sys.argv[i + 1])
        return tracker.reconcile(sys.argv[i + 1])
    print("  sync: tracker mirror")
    return tracker.next_step(d, cfg, L.paths()["root"])


def main():
    if "--actual" in sys.argv and "--tracker" not in sys.argv:
        print("  sync: usage: sync.py --tracker --actual <file> (--actual only goes with --tracker)")
        return 2
    if not L.has_plan():
        if "--tracker" in sys.argv:
            print("  sync: --tracker needs a plan (plan/plan.json); there is none in this project")
            return 2
        return 0
    p = L.paths()
    if "--live-revision" in sys.argv:
        i = sys.argv.index("--live-revision")
        sha = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
        if not (7 <= len(sha) <= 40 and all(c in "0123456789abcdef" for c in sha.lower())):
            print("  sync: --live-revision needs a hex commit (7 to 40 chars), got %r" % sha)
            return 2
        d = L.load()
        if d.setdefault("facts", {}).get("live_revision") != sha:
            d["facts"]["live_revision"] = sha
            L.save(d, p["root"])
            print("  sync: facts.live_revision = %s" % sha)
        else:
            print("  sync: facts.live_revision already %s" % sha)
    if "--no-roll" not in sys.argv and L.mode(L.load()) == "full":
        r = L.roll(p["root"])
        if "new" in r:
            print("  sync: rolled done %d, changelog %d, queued %d into %s/ in full (%d -> %d KB)"
                  % (r["done"], r["changelog"], r["next"],
                     os.path.relpath(os.path.join(p["dir"], L.ARCHIVE_DIRNAME), p["root"]),
                     r["before"] // 1024, r["after"] // 1024))
    # Views are refreshed in both modes: declared views are opt-in, then checked.
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
    # Flush first: when stdout is a pipe, our lines would otherwise print AFTER
    # the children's, and "rolled ..." would read as happening after the gate.
    sys.stdout.flush()
    tracker_rc, gate_rc = 0, 0
    for script in ("render.py", "check.py"):
        if script == "check.py" and "--tracker" in sys.argv:
            tracker_rc = tracker_step()
            sys.stdout.flush()
        argv = [sys.executable, os.path.join(HERE, script)]
        if script == "check.py":
            argv += ["--event", "sync"]  # "sync"
        r = subprocess.run(argv)
        if script == "check.py":
            gate_rc = r.returncode or 0
    # Unreadable tracker input is 2 whatever the gate said: nothing was compared.
    if tracker_rc == 2:
        return 2
    return gate_rc or tracker_rc


if __name__ == "__main__":
    sys.exit(main())
