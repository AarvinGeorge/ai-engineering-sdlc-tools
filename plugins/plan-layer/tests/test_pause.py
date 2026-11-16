"""Pause and handoff: pause.py writes plan/HANDOFF.md (an on-call handover note),
sets meta.paused, and --resume clears it. Every number in the note is read at
the moment of writing."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_light_and_budget import Base, run  # noqa: E402


def item(name, stage="intent", **kw):
    d = {"name": name, "why": "w", "unblocks": "u", "stage": stage, "plan_file": None}
    d.update(kw)
    return d


class PauseBase(Base):
    def setUp(self):
        super().setUp()
        self.d["plans"]["now"] = [item("E-01.S2 Login page", "building", plan_file="docs/p.md",
                                       status="wiring the form", updated="2026-01-01",
                                       tasks=[{"name": "t", "state": "todo"}])]
        self.d["plans"]["next"] = [item("E-01.S3 Logout page"), item("E-01.S4 Profile page")]
        self.d["parked"] = [{"id": "P1", "q": "Should sessions expire?", "trigger": "before launch"}]
        self.d["invariants"] = [{"rule": "Passwords are never logged", "state": "broken"}]
        self.write()

    def handoff(self):
        return open(os.path.join(self.dir, "plan", "HANDOFF.md"), encoding="utf-8").read()

    def pause(self, *args):
        return run("pause.py", *args, project=self.dir)


class TestPause(PauseBase):
    def test_writes_handoff_with_every_section(self):
        r = self.pause()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        t = self.handoff()
        for needle in ("ACTIVE NOW", "E-01.S2 Login page", "wiring the form", "Resume order",
                       "E-01.S3 Logout page", "Should sessions expire?", "before launch",
                       "Traps", "Passwords are never logged", "Gate", "re-read before citing"):
            self.assertIn(needle, t)
        self.assertLess(t.index("E-01.S2 Login page"), t.index("E-01.S3 Logout page"),
                        "resume order is now, then next")
        self.assertLess(t.index("E-01.S3"), t.index("E-01.S4"))

    def test_time_is_read_now_in_utc_and_stated(self):
        self.pause()
        m = re.search(r"read at (\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ); re-read before citing", self.handoff())
        self.assertIsNotNone(m, self.handoff())
        self.assertGreater(m.group(1), "2026-11-01")
        at = self.read()["meta"]["paused"]["at"]
        self.assertEqual(at, m.group(1))

    def test_git_facts_are_measured_now(self):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e.x",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e.x")
        subprocess.run(["git", "checkout", "-q", "-b", "feature-x"], cwd=self.dir, check=True)
        subprocess.run(["git", "add", "-A"], cwd=self.dir, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=self.dir, check=True, env=env)
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=self.dir,
                              capture_output=True, text=True).stdout.strip()
        for n in ("a.txt", "b.txt"):
            open(os.path.join(self.dir, n), "w").write("x")
        self.pause()
        t = self.handoff()
        self.assertIn("feature-x", t)
        self.assertIn(head, t)
        self.assertIn("2 uncommitted file(s)", t)

    def test_not_a_git_repo_is_said_plainly(self):
        shutil.rmtree(os.path.join(self.dir, ".git"))
        d2 = tempfile.mkdtemp(prefix="planlayer-nogit-")
        try:
            shutil.copytree(os.path.join(self.dir, "plan"), os.path.join(d2, "plan"))
            r = run("pause.py", project=d2)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("not a git repo", open(os.path.join(d2, "plan", "HANDOFF.md")).read())
        finally:
            shutil.rmtree(d2, ignore_errors=True)

    def test_gate_result_and_traps_are_listed(self):
        self.d["plans"]["now"][0]["tasks"] = [{"name": "t", "state": "weird"}]
        self.write()
        self.pause()
        t = self.handoff()
        self.assertIn("FAIL", t)
        self.assertIn("task", t.lower())
        self.assertIn("Passwords are never logged", t.split("Traps")[1])

    def test_sets_paused_bumps_updated_and_leaves_page_current(self):
        r = self.pause()
        d = self.read()
        self.assertTrue(d["meta"]["paused"]["at"].endswith("Z"))
        self.assertGreater(d["meta"]["updated"], "2026-11-01")
        _, fails, _ = self.gate()
        self.assertEqual([f for f in fails if "rendered from a different" in f], [], fails)

    def test_prints_reminder_to_stop_recurring_work(self):
        r = self.pause()
        self.assertIn("recurring", r.stdout)
        self.assertIn("scheduled", r.stdout)

    def test_no_plan_is_a_quiet_noop(self):
        d2 = tempfile.mkdtemp(prefix="planlayer-noplan-")
        try:
            r = run("pause.py", project=d2)
            self.assertEqual(r.returncode, 0)
            self.assertFalse(os.path.exists(os.path.join(d2, "plan")))
        finally:
            shutil.rmtree(d2, ignore_errors=True)

    def test_repause_refreshes_the_stamp(self):
        self.pause()
        first = self.read()["meta"]["paused"]["at"]
        self.pause()
        self.assertGreaterEqual(self.read()["meta"]["paused"]["at"], first)


class TestResume(PauseBase):
    def test_resume_clears_paused_and_marks_the_note(self):
        self.pause()
        r = self.pause("--resume")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("paused", self.read()["meta"])
        t = self.handoff()
        self.assertIn("RESUMED", t.splitlines()[2] if len(t.splitlines()) > 2 else t)
        self.assertIn("ACTIVE NOW", t, "the note stays")
        _, fails, _ = self.gate()
        self.assertEqual([f for f in fails if "rendered from a different" in f], [], fails)

    def test_resume_when_not_paused_changes_nothing(self):
        before = open(os.path.join(self.dir, "plan", "plan.json")).read()
        r = self.pause("--resume")
        self.assertEqual(r.returncode, 0)
        self.assertIn("not paused", r.stdout)
        self.assertEqual(open(os.path.join(self.dir, "plan", "plan.json")).read(), before)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "plan", "HANDOFF.md")))


class TestBriefAndGate(PauseBase):
    def brief(self):
        r = run("brief.py", "--session-start", project=self.dir)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]

    def test_paused_first_line(self):
        self.pause()
        at = self.read()["meta"]["paused"]["at"]
        first = self.brief().splitlines()[0]
        self.assertEqual(first, "PAUSED at %s \u2014 read plan/HANDOFF.md before anything else" % at)

    def test_not_paused_has_no_such_line(self):
        self.assertNotIn("PAUSED", self.brief())

    def test_resumed_has_no_such_line(self):
        self.pause()
        self.pause("--resume")
        self.assertNotIn("PAUSED", self.brief())

    def test_malformed_paused_fails_the_gate(self):
        for bad in ("yesterday", {"at": "yesterday"}, {}, None):
            self.d["meta"]["paused"] = bad
            self.write()
            _, fails, _ = self.gate()
            self.assertEqual(len([f for f in fails if "meta.paused" in f]), 1, (bad, fails))

    def test_paused_flows_into_tracker_expected_status(self):
        self.d["meta"]["tracker"] = {"kind": "notion", "target": "x"}
        self.write()
        self.pause()
        r = run("tracker.py", "expected", project=self.dir)
        rows = json.loads(r.stdout)["rows"]
        self.assertEqual(rows[0]["Status"], "Paused")


if __name__ == "__main__":
    unittest.main()
