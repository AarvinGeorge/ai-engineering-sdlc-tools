"""0.16.0: sync rolls automatically, the size budget lives in meta, and light mode."""
import json
import os
import shutil
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
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = project
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] + list(args),
                          cwd=project, env=env, capture_output=True, text=True)


class Base(unittest.TestCase):
    template = "plan.json"

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="planlayer016-")
        subprocess.run(["git", "init", "-q"], cwd=self.dir, check=True)
        os.makedirs(os.path.join(self.dir, "plan"))
        with open(os.path.join(PLUGIN, "templates", self.template)) as fh:
            self.d = json.load(fh)
        self.d["meta"]["updated"] = "2026-01-01T00:00:00Z"
        self.d["meta"]["changelog"][0]["date"] = "2026-01-01"

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self):
        with open(os.path.join(self.dir, "plan", "plan.json"), "w") as fh:
            json.dump(self.d, fh, indent=2)

    def read(self):
        return json.load(open(os.path.join(self.dir, "plan", "plan.json")))

    def archive(self, name):
        p = os.path.join(self.dir, "plan", "archive", name + ".json")
        return json.load(open(p)) if os.path.isfile(p) else None

    def history(self):
        """12 finished items and 15 changelog entries: 4 and 5 are due to roll."""
        self.d["meta"]["changelog"] = [{"version": "0.0.%d" % i, "date": "2026-01-01", "note": "n%d" % i}
                                       for i in range(15)]
        self.d["meta"]["plan_version"] = "0.0.14"
        self.d["plans"]["done"] = [{"name": "done %d" % i, "period": "2026-01-01", "outcome": "o"}
                                   for i in range(12)]

    def gate(self):
        render = run("render.py", project=self.dir)
        self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
        r = run("check.py", "--json", project=self.dir)
        out = json.loads(r.stdout)
        return r.returncode, out["fails"], out["drifts"]


# ------------------------------------------------------------------ gap 1
class TestSyncRolls(Base):
    def test_sync_rolls_when_rollable_records_exist(self):
        self.history()
        self.write()
        r = run("sync.py", project=self.dir)
        d = self.read()
        self.assertEqual(len(d["plans"]["done"]), 8, r.stdout + r.stderr)
        self.assertEqual(len(d["meta"]["changelog"]), 10)
        self.assertEqual([x["name"] for x in self.archive("done")], ["done %d" % i for i in range(4)],
                         "rolled in full, oldest first")
        self.assertIn("sync: rolled", r.stdout)
        self.assertNotIn("aged off", r.stdout, "the gate after the roll has nothing left to roll")
        self.assertLess(r.stdout.index("sync: rolled"), r.stdout.index("wrote "),
                        "the roll line prints before the render and the gate, in the order they ran")

    def test_no_roll_leaves_them(self):
        self.history()
        self.write()
        r = run("sync.py", "--no-roll", project=self.dir)
        self.assertEqual(len(self.read()["plans"]["done"]), 12, r.stdout + r.stderr)
        self.assertIsNone(self.archive("done"))
        self.assertNotIn("sync: rolled", r.stdout)
        self.assertIn("aged off", r.stdout, "the gate still says the records are due")

    def test_nothing_due_means_no_archive_and_no_message(self):
        self.write()
        r = run("sync.py", project=self.dir)
        self.assertFalse(os.path.isdir(os.path.join(self.dir, "plan", "archive")), r.stdout)
        self.assertNotIn("sync: rolled", r.stdout)


class TestSizeBudget(Base):
    def pad(self, kb):
        self.d["glossary"] = [{"term": "T%d" % i, "means": "x" * 1000} for i in range(kb)]

    def size_drifts(self, drifts):
        return [x for x in drifts if "KB" in x and "plan.json is" in x]

    def test_budget_helper(self):
        self.assertEqual(L.size_budget_kb({}), 200)
        self.assertEqual(L.size_budget_kb({"meta": {}}), 200)
        self.assertEqual(L.size_budget_kb({"meta": {"size_budget_kb": 64}}), 64)

    def test_budget_is_read_from_meta(self):
        self.pad(30)
        self.d["meta"]["size_budget_kb"] = 16
        self.write()
        _, fails, drifts = self.gate()
        self.assertEqual(len(self.size_drifts(drifts)), 1, drifts)
        self.assertIn("budget 16 KB", self.size_drifts(drifts)[0])
        self.assertIn("meta.size_budget_kb", self.size_drifts(drifts)[0])

    def test_default_budget_unchanged(self):
        self.pad(30)
        self.write()
        _, _, drifts = self.gate()
        self.assertEqual(self.size_drifts(drifts), [], "30 KB is under the 200 KB default")

    def test_a_raised_budget_silences_the_default(self):
        self.pad(210)
        self.write()
        _, _, drifts = self.gate()
        self.assertEqual(len(self.size_drifts(drifts)), 1, "over the default")
        self.d["meta"]["size_budget_kb"] = 400
        self.write()
        _, _, drifts = self.gate()
        self.assertEqual(self.size_drifts(drifts), [], drifts)

    def test_a_nonsense_budget_fails(self):
        for bad in (0, -5, "big", True):
            self.d["meta"]["size_budget_kb"] = bad
            self.write()
            _, fails, _ = self.gate()
            self.assertTrue(any("size_budget_kb" in f for f in fails), (bad, fails))


# ------------------------------------------------------------------ gap 2
class TestLightTemplate(Base):
    template = "plan.light.json"

    def test_template_declares_light_and_is_small(self):
        self.assertEqual(self.d["meta"]["mode"], "light")
        self.assertNotIn("views", self.d)
        self.assertLess(os.path.getsize(os.path.join(PLUGIN, "templates", "plan.light.json")), 1500)

    def test_light_plan_with_no_views_passes_the_gate(self):
        self.write()
        code, fails, drifts = self.gate()
        self.assertEqual((code, fails), (0, []), fails)

    def test_light_plan_that_contradicts_itself_still_fails(self):
        self.d["capabilities"][0]["build"] = "done"
        self.d["capabilities"][0]["evidence"] = ""
        self.write()
        code, fails, _ = self.gate()
        self.assertEqual(code, 1)
        self.assertTrue(any("carries no evidence" in f for f in fails), fails)


class TestLightModeSkipsFullOnlyChecks(Base):
    def full_only_material(self):
        """Things that drift in full mode: a view whose spec is gone, a live revision,
        a figure reading a missing fact, and history due to roll."""
        self.history()
        self.d["views"] = [{"label": "topology", "spec": "plan/archify/missing.json", "spec_sha256": "ab" * 32}]
        self.d.setdefault("facts", {})["live_revision"] = "abcdef1"
        with open(os.path.join(self.dir, "plan", "figures.py"), "w") as fh:
            fh.write("x = F.get('nowhere')\n")

    def test_full_mode_still_drifts_on_them(self):
        self.full_only_material()
        self.write()
        _, _, drifts = self.gate()
        text = "\n".join(drifts)
        for needle in ("not on disk", "aged off", "fact 'nowhere'"):
            self.assertIn(needle, text)

    def test_light_mode_does_not(self):
        self.full_only_material()
        self.d["meta"]["mode"] = "light"
        self.write()
        _, fails, drifts = self.gate()
        text = "\n".join(fails + drifts)
        for needle in ("not on disk", "aged off", "nowhere", "live revision", "spec"):
            self.assertNotIn(needle, text)

    def test_sync_does_not_roll_a_light_plan(self):
        self.history()
        self.d["meta"]["mode"] = "light"
        self.write()
        r = run("sync.py", project=self.dir)
        self.assertEqual(len(self.read()["plans"]["done"]), 12, r.stdout)
        self.assertIsNone(self.archive("done"))

    def test_mode_helper_and_unknown_mode_fails(self):
        self.assertEqual(L.mode({}), "full")
        self.assertEqual(L.mode({"meta": {"mode": "light"}}), "light")
        self.d["meta"]["mode"] = "lite"
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue(any("meta.mode" in f for f in fails), fails)


if __name__ == "__main__":
    unittest.main()
