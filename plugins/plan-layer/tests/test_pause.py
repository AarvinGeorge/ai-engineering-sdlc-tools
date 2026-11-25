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


class TestArgs(PauseBase):
    def test_unknown_argument_is_usage_and_pauses_nothing(self):
        for arg in ("--help", "-h", "--bogus"):
            r = self.pause(arg)
            self.assertEqual(r.returncode, 2, (arg, r.stdout))
            self.assertIn("usage", (r.stdout + r.stderr).lower())
        self.assertNotIn("paused", self.read()["meta"])
        self.assertFalse(os.path.exists(os.path.join(self.dir, "plan", "HANDOFF.md")))

    def test_tells_the_agent_to_sync_the_tracker_when_one_is_set(self):
        self.assertNotIn("sync.py --tracker", self.pause().stdout)
        self.d["meta"]["tracker"] = {"kind": "notion", "target": "x"}
        self.write()
        self.assertIn("sync.py --tracker", self.pause().stdout)


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


def git(cwd, *a):
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t"] + list(a),
                   cwd=cwd, check=True, capture_output=True)


class TestHandoffReconcile(PauseBase):
    def setUp(self):
        super().setUp()
        self.d["meta"]["naming"] = "work-ids"
        self.d["meta"]["controller"] = {"one_writer": False, "decision_log": "docs/decisions.md"}
        self.d["meta"]["tracker"] = {"kind": "notion", "target": "db-1"}
        os.makedirs(os.path.join(self.dir, "docs"))
        open(os.path.join(self.dir, "docs", "decisions.md"), "w").write("# Decisions\n")
        self.write()
        git(self.dir, "checkout", "-q", "-b", "main")
        git(self.dir, "add", "-A")
        git(self.dir, "commit", "-q", "-m", "base")
        git(self.dir, "checkout", "-q", "-b", "e-01-login")

    def test_without_controller_the_note_is_as_before(self):
        self.d["meta"].pop("controller")
        self.write()
        self.pause()
        self.assertNotIn("## Reconcile", self.handoff())

    def test_reconcile_section_lists_the_open_diff(self):
        r = self.pause()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        h = self.handoff()
        self.assertIn("## Reconcile", h)
        self.assertIn("never reconciled", h)
        self.assertIn("CONTROLLER:", r.stdout)

    def test_git_per_active_item_names_branch_and_last_commit(self):
        open(os.path.join(self.dir, "x.txt"), "w").write("x")
        git(self.dir, "add", "x.txt")
        git(self.dir, "commit", "-q", "-m", "E-01.S2: wire the form")
        self.pause()
        h = self.handoff()
        self.assertIn("## Git per active item", h)
        self.assertIn("e-01-login", h)
        self.assertIn("E-01.S2: wire the form", h)

    def test_decisions_added_since_the_last_handoff(self):
        self.pause()
        with open(os.path.join(self.dir, "docs", "decisions.md"), "a") as fh:
            fh.write("- D-001 sessions expire after a day\n- D-002 no remember-me box\n")
        git(self.dir, "add", "-A")
        git(self.dir, "commit", "-q", "-m", "decisions")
        self.pause()
        h = self.handoff()
        self.assertIn("## Decisions since the last handoff", h)
        self.assertIn("D-001", h)
        self.assertIn("D-002", h)
        self.assertIn("transcript", h)

    def test_handoff_head_is_recorded(self):
        self.pause()
        st = json.load(open(os.path.join(self.dir, "plan", "controller-state.json")))
        self.assertEqual(len(st["handoff"]["head"]), 40)

    def decisions(self):
        h = self.handoff()
        return h.split("## Decisions since the last handoff")[1].split("\n## ")[0]

    def test_unknown_previous_head_falls_back_to_merge_base_and_says_so(self):
        self.pause()
        stp = os.path.join(self.dir, "plan", "controller-state.json")
        st = json.load(open(stp))
        st["handoff"]["head"] = "0" * 40
        json.dump(st, open(stp, "w"))
        with open(os.path.join(self.dir, "docs", "decisions.md"), "a") as fh:
            fh.write("- D-010 later decision\n")
        git(self.dir, "add", "-A")
        git(self.dir, "commit", "-q", "-m", "decisions")
        self.pause()
        t = self.decisions()
        self.assertIn("D-010", t)
        self.assertIn("merge-base", t)
        self.assertNotIn("none", t)

    def test_untracked_decision_log_is_cannot_measure_not_none(self):
        git(self.dir, "rm", "-q", "--cached", "docs/decisions.md")
        with open(os.path.join(self.dir, "docs", "decisions.md"), "a") as fh:
            fh.write("- D-010 not yet committed\n")
        self.pause()
        t = self.decisions()
        self.assertIn("cannot measure", t)
        self.assertNotIn("none", t)

    def test_missing_decision_log_is_cannot_measure_not_none(self):
        git(self.dir, "rm", "-q", "-f", "docs/decisions.md")
        self.pause()
        t = self.decisions()
        self.assertIn("cannot measure", t)
        self.assertNotIn("none", t)

    def test_unreadable_controller_state_is_kept_and_said(self):
        stp = os.path.join(self.dir, "plan", "controller-state.json")
        open(stp, "w").write("<<<<<<< broken")
        r = self.pause()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(open(stp).read(), "<<<<<<< broken")
        self.assertIn("handoff record not written: controller-state.json unreadable", self.handoff())

    def test_epic_slug_and_work_id_do_not_match_longer_ones(self):
        self.d["plans"]["now"][0]["name"] = "E-01.S2 Login page"
        self.write()
        git(self.dir, "branch", "e-010-other")
        open(os.path.join(self.dir, "y.txt"), "w").write("y")
        git(self.dir, "add", "y.txt")
        git(self.dir, "commit", "-q", "-m", "E-01.S20: someone else")
        self.pause()
        t = self.handoff().split("## Git per active item")[1].split("\n## ")[0]
        self.assertNotIn("e-010-other", t)
        self.assertNotIn("S20", t)

    def test_pause_under_one_writer_keeps_the_gate_clean(self):
        self.d["meta"]["controller"]["one_writer"] = True
        self.d["meta"].pop("tracker")
        self.write()
        self.assertEqual(run("move.py", "--adopt", project=self.dir).returncode, 0)
        r = self.pause()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = run("move.py", "E-01.S2", "--status", "after pause", project=self.dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = run("check.py", "--json", project=self.dir)
        found = json.loads(r.stdout).get("controller", [])
        self.assertEqual([f for f in found if f["level"] == "FAIL"], [], found)


if __name__ == "__main__":
    unittest.main()
