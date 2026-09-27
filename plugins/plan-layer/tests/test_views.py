"""Views (0.15.0): drawings published beside the page, kept honest by the gate and sync.py."""
import hashlib, json, os, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__)); PLUGIN = os.path.dirname(HERE); SCRIPTS = os.path.join(PLUGIN, "scripts")
sys.path.insert(0, SCRIPTS)
import plan_lib as L  # noqa: E402


def run(script, *args, project):
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] + list(args), cwd=project, capture_output=True, text=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.dir = self.tmp.name
        subprocess.run(["git", "init", "-q"], cwd=self.dir, check=True)
        os.makedirs(os.path.join(self.dir, "plan", "archify"))
        with open(os.path.join(PLUGIN, "templates", "plan.json")) as fh:
            self.d = json.load(fh)
        self.d["meta"]["updated"] = "2026-01-01T00:00:00Z"; self.d["meta"]["changelog"][0]["date"] = "2026-01-01"
        self.spec = {"schema_version": 1, "diagram_type": "architecture",
                     "meta": {"title": "t", "repository": {"url": "https://example.test/r", "revision": "a" * 40}},
                     "components": []}
        self.write_spec()
        self.d["views"] = [{"figure": "x", "label": "Topology", "spec": "plan/archify/t.architecture.json", "url": "https://example.test/a"}]
        self.write()

    def tearDown(self): self.tmp.cleanup()
    def write(self):
        with open(os.path.join(self.dir, "plan", "plan.json"), "w") as fh: json.dump(self.d, fh, indent=2)
    def write_spec(self):
        with open(os.path.join(self.dir, "plan", "archify", "t.architecture.json"), "w") as fh: json.dump(self.spec, fh)
    def read(self): return json.load(open(os.path.join(self.dir, "plan", "plan.json")))


class TestSync(Base):
    def test_sync_records_sha_and_revision_from_the_files(self):
        r = run("sync.py", project=self.dir); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        v = self.read()["views"][0]
        self.assertEqual(v["revision"], "a" * 40)
        self.assertEqual(v["spec_sha256"], L.sha256_file(os.path.join(self.dir, "plan", "archify", "t.architecture.json")))
        self.assertIn("views refreshed (2 field(s) changed)", r.stdout)

    def test_sync_is_idempotent(self):
        run("sync.py", project=self.dir); r = run("sync.py", project=self.dir)
        self.assertIn("(0 field(s) changed)", r.stdout)

    def test_sync_refuses_a_missing_spec(self):
        os.remove(os.path.join(self.dir, "plan", "archify", "t.architecture.json"))
        r = run("sync.py", project=self.dir); self.assertEqual(r.returncode, 2); self.assertIn("missing on disk", r.stdout)


class TestGate(Base):
    def test_no_drift_when_recorded_facts_match(self):
        run("sync.py", project=self.dir); r = run("check.py", project=self.dir)
        self.assertNotIn("view 'Topology'", r.stdout)

    def test_drift_when_the_spec_changes_after_delivery(self):
        run("sync.py", project=self.dir)
        self.spec["components"].append({"id": "n", "type": "backend", "label": "New"}); self.write_spec()
        run("render.py", project=self.dir); r = run("check.py", project=self.dir)
        self.assertIn("the spec changed since it was delivered", r.stdout)

    def test_drift_when_the_live_revision_moves_past_the_drawing(self):
        run("sync.py", project=self.dir)
        d = self.read(); d.setdefault("facts", {})["live_revision"] = "b" * 40; self.d = d; self.write()
        run("render.py", project=self.dir); r = run("check.py", project=self.dir)
        self.assertIn("was measured at aaaaaaaaaaaa but the live revision is bbbbbbbbbbbb", r.stdout)

    def test_short_and_long_revisions_agree(self):
        run("sync.py", project=self.dir)
        d = self.read(); d.setdefault("facts", {})["live_revision"] = "a" * 12; self.d = d; self.write()
        run("render.py", project=self.dir); r = run("check.py", project=self.dir)
        self.assertNotIn("live revision", r.stdout)

    def test_missing_spec_is_named_not_ignored(self):
        os.remove(os.path.join(self.dir, "plan", "archify", "t.architecture.json"))
        run("render.py", project=self.dir); r = run("check.py", project=self.dir)
        self.assertIn("is not on disk", r.stdout)


if __name__ == "__main__":
    unittest.main()


class TestLiveRevision(Base):
    def test_live_revision_is_recorded_then_idempotent(self):
        r = run("sync.py", "--live-revision", "c" * 40, project=self.dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.read()["facts"]["live_revision"], "c" * 40)
        r = run("sync.py", "--live-revision", "c" * 40, project=self.dir)
        self.assertIn("already", r.stdout)

    def test_live_revision_refuses_a_non_commit(self):
        r = run("sync.py", "--live-revision", "not-a-sha", project=self.dir)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("live_revision", json.dumps(self.read().get("facts", {})))
