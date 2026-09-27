"""roll.py, the roll-due drift signal, and the archive hints on the page (0.14.0)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
SCRIPTS = os.path.join(PLUGIN, "scripts")
sys.path.insert(0, SCRIPTS)
import plan_lib as L  # noqa: E402


def run(script, *args, project):
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] + list(args),
                          cwd=project, capture_output=True, text=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        subprocess.run(["git", "init", "-q"], cwd=self.dir, check=True)
        os.makedirs(os.path.join(self.dir, "plan"))
        with open(os.path.join(PLUGIN, "templates", "plan.json")) as fh:
            self.d = json.load(fh)
        self.d["meta"]["updated"] = "2026-01-01T00:00:00Z"
        self.d["meta"]["changelog"] = [{"version": "0.0.%d" % i, "date": "2026-01-01", "note": "n%d" % i}
                                       for i in range(15)]
        self.d["meta"]["plan_version"] = "0.0.14"
        self.d["plans"]["done"] = [{"name": "done %d" % i, "period": "2026-01-01", "outcome": "o"} for i in range(12)]
        # 12 queued items over three capabilities; capability 3 appears only at position 11
        self.d["plans"]["next"] = [{"name": "next %d" % i, "stage": "intent", "capability": 1 if i < 6 else 2,
                                    "why": "w", "unblocks": "u"} for i in range(11)]
        self.d["plans"]["next"].append({"name": "only one for cap 3", "stage": "intent", "capability": 3,
                                        "why": "w", "unblocks": "u"})
        self.write()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self):
        with open(os.path.join(self.dir, "plan", "plan.json"), "w") as fh:
            json.dump(self.d, fh, indent=2)

    def read(self):
        return json.load(open(os.path.join(self.dir, "plan", "plan.json")))

    def archive(self, name):
        p = os.path.join(self.dir, "plan", "archive", name + ".json")
        return json.load(open(p)) if os.path.isfile(p) else None


class TestRollable(unittest.TestCase):
    def test_rules_are_pure_and_keep_one_per_capability(self):
        # nine EQUAL dicts on purpose: rolling must go by item, not by value
        d = {"plans": {"done": list(range(10)), "next": [{"capability": 1} for _ in range(9)] + [{"capability": 2}]},
             "meta": {"changelog": list(range(12))}}
        r = L.rollable(d, L.ROLL_DEFAULTS)
        self.assertEqual(r["done"], [0, 1])
        self.assertEqual(r["changelog"], [0, 1])
        self.assertEqual(len(r["keep_next"]), 9, "the lone capability-2 item must be kept")
        self.assertEqual(r["next"], [{"capability": 1}], "the ninth capability-1 item rolls off even though it equals the others")
        self.assertEqual(d["plans"]["done"], list(range(10)), "rollable must not mutate")


class TestRoll(Base):
    def test_dry_run_moves_nothing(self):
        r = run("roll.py", "--dry-run", project=self.dir)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("would move done: 4  changelog: 5  queued-to-backlog: 3", r.stdout)
        self.assertEqual(len(self.read()["plans"]["done"]), 12)
        self.assertIsNone(self.archive("done"))

    def test_roll_moves_in_full_and_keeps_the_lone_capability(self):
        r = run("roll.py", project=self.dir)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = self.read()
        self.assertEqual([x["name"] for x in d["plans"]["done"]], ["done %d" % i for i in range(4, 12)])
        self.assertEqual(len(d["meta"]["changelog"]), 10)
        names = [x["name"] for x in d["plans"]["next"]]
        self.assertEqual(len(names), 9)
        self.assertIn("only one for cap 3", names)
        self.assertEqual([x["name"] for x in self.archive("done")], ["done %d" % i for i in range(4)])
        self.assertEqual(len(self.archive("changelog")), 5)
        self.assertEqual(len(self.archive("backlog")), 3)
        # every archived record is intact, not a summary
        self.assertEqual(self.archive("done")[0], {"name": "done 0", "period": "2026-01-01", "outcome": "o"})

    def test_roll_twice_is_idempotent(self):
        run("roll.py", project=self.dir)
        r = run("roll.py", project=self.dir)
        self.assertIn("moving done: 0  changelog: 0  queued-to-backlog: 0", r.stdout)
        self.assertEqual(len(self.archive("done")), 4, "a second run must not duplicate archive records")

    def test_config_overrides_keep(self):
        with open(os.path.join(self.dir, ".plan-layer.json"), "w") as fh:
            json.dump({"roll": {"keep_done": 2, "keep_log": 3, "keep_next": 1}}, fh)
        run("roll.py", project=self.dir)
        d = self.read()
        self.assertEqual(len(d["plans"]["done"]), 2)
        self.assertEqual(len(d["meta"]["changelog"]), 3)
        # 1 kept by position, plus the first of capability 2 and the lone capability 3
        self.assertEqual(len(d["plans"]["next"]), 3)

    def test_silent_without_a_plan(self):
        os.remove(os.path.join(self.dir, "plan", "plan.json"))
        r = run("roll.py", project=self.dir)
        self.assertEqual((r.returncode, r.stdout), (0, ""))


class TestGateAndPage(Base):
    def test_gate_reports_roll_due_then_clears(self):
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertIn("aged off the front page (done 4, changelog 5, queued 3)", r.stdout)
        self.assertIn("roll.py", r.stdout)
        run("roll.py", project=self.dir)
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertNotIn("aged off the front page", r.stdout)

    def test_page_hint_counts_from_the_archive_file(self):
        run("roll.py", project=self.dir)
        run("render.py", project=self.dir)
        page = open(os.path.join(self.dir, "plan", "index.html"), encoding="utf-8").read()
        self.assertIn("4 older in archive/done.json", page)
        self.assertIn("3 more in archive/backlog.json", page)

    def test_page_has_no_archive_hint_before_any_roll(self):
        run("render.py", project=self.dir)
        page = open(os.path.join(self.dir, "plan", "index.html"), encoding="utf-8").read()
        self.assertNotIn("archive/done.json", page)


if __name__ == "__main__":
    unittest.main()
