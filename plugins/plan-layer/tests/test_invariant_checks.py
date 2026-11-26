"""Invariants that can be run: an optional `check` command, explicit --verify only.

What: tests that check.py --verify runs invariant checks, reports a failing one
as a FAIL naming the invariant, and that nothing else ever runs them.
Use when: the plugin's normal suite (python -m unittest tests/*.py).
Inputs: temporary plan projects. Output: unittest results.
Side effects: creates and removes temporary directories.
Role: keeps the explicit-only security property and the FAIL contract tested.
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_plan_layer import Base, run  # noqa: E402


class InvariantChecks(Base):
    def plan_with(self, invariants, assertions=None):
        d = self.make_plan()
        d["invariants"] = invariants
        if assertions is not None:
            d["assertions"] = assertions
        self.write(d)
        run("render.py", project=self.dir)
        return d

    def stamp(self):
        with open(os.path.join(self.dir, "plan", "plan.json")) as fh:
            return json.load(fh)["meta"].get("assertions_verified")

    def test_passing_check_holds_and_exits_zero(self):
        self.plan_with([{"rule": "suite green", "state": "holding", "check": "true"}])
        r = run("check.py", "--verify", project=self.dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("HOLDS", r.stdout)
        self.assertIn("suite green", r.stdout)

    def test_failing_check_is_a_fail_naming_the_invariant(self):
        self.plan_with([{"rule": "no debug prints", "state": "holding", "check": "exit 3"}])
        r = run("check.py", "--verify", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertRegex(r.stdout, r"FAIL\s+invariant 'no debug prints' \(state 'holding'\)")
        self.assertIn("exited 3", r.stdout)

    def test_failing_check_does_not_move_the_stamp(self):
        d = self.plan_with([{"rule": "x", "state": "holding", "check": "false"}])
        d["meta"]["assertions_verified"] = "2020-01-01T00:00:00Z"
        self.write(d)
        run("check.py", "--verify", project=self.dir)
        self.assertEqual(self.stamp(), "2020-01-01T00:00:00Z")

    def test_clean_run_with_only_invariant_checks_stamps(self):
        self.plan_with([{"rule": "x", "state": "holding", "check": "true"}])
        r = run("check.py", "--verify", project=self.dir)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue((self.stamp() or "").endswith("Z"))

    def test_checks_read_plan_facts_from_setup(self):
        d = self.make_plan()
        d["assertions_setup"] = "echo up=yes"
        d["invariants"] = [{"rule": "service up", "state": "holding",
                            "check": "grep -c '^up=yes$' \"$PLAN_FACTS\""}]
        self.write(d)
        r = run("check.py", "--verify", project=self.dir)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("HOLDS", r.stdout)

    def test_assertions_and_invariants_both_run(self):
        self.plan_with([{"rule": "inv", "state": "holding", "check": "false"}],
                       assertions=[{"claim": "echo", "run": "echo hi", "expect": "hi"}])
        r = run("check.py", "--verify", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("MATCH", r.stdout)
        self.assertIn("FAIL", r.stdout)

    def test_invariant_without_check_is_not_run_or_reported(self):
        self.plan_with([{"rule": "hand-set", "state": "holding"}])
        r = run("check.py", "--verify", project=self.dir)
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("hand-set", r.stdout)

    def test_never_run_without_verify(self):
        """A repository must not execute its author's commands by being opened."""
        sentinel = os.path.join(self.dir, "SHOULD_NOT_EXIST")
        self.plan_with([{"rule": "malicious", "state": "holding",
                         "check": "touch %s" % sentinel}])
        run("brief.py", "--session-start", project=self.dir)
        run("brief.py", "--pre-compact", project=self.dir)
        run("check.py", project=self.dir)
        run("check.py", "--json", project=self.dir)
        run("sync.py", project=self.dir)
        run("gate_hook.py", project=self.dir)
        run("check.py", "--strict", project=self.dir)
        for ev in ("stop", "session-start", "sync", "pause"):
            run("check.py", "--event", ev, project=self.dir)
        run("pause.py", project=self.dir)
        run("pause.py", "--resume", project=self.dir)
        run("move.py", "--adopt", project=self.dir)
        run("render.py", project=self.dir)
        run("roll.py", project=self.dir)
        run("roll.py", "--dry-run", project=self.dir)
        self.assertFalse(os.path.exists(sentinel), "an invariant check ran without --verify")

    def test_malformed_check_fails_verify_and_keeps_the_stamp(self):
        for bad in ("   ", ["false"], None):
            d = self.plan_with([{"rule": "bad", "state": "holding", "check": bad}])
            d["meta"]["assertions_verified"] = "2020-01-01T00:00:00Z"
            self.write(d)
            r = run("check.py", "--verify", project=self.dir)
            self.assertEqual(r.returncode, 1, repr(bad))
            self.assertIn("FAIL    invariant 'bad': check is not a runnable command", r.stdout)
            self.assertEqual(self.stamp(), "2020-01-01T00:00:00Z", repr(bad))

    def test_non_string_check_is_a_structural_fail(self):
        self.plan_with([{"rule": "bad", "state": "holding", "check": ["true"]}])
        r = run("check.py", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("invariant 'bad': check must be a non-empty shell command", r.stdout)

    def test_declared_checks_never_run_drift(self):
        self.plan_with([{"rule": "x", "state": "holding", "check": "true"}])
        self.assertIn("never recorded as run", run("check.py", project=self.dir).stdout)

    def verify_text(self, **kw):
        """Run check.verify in-process with a short timeout; return its stdout."""
        import contextlib
        import io
        import check
        old_env = os.environ.get("CLAUDE_PROJECT_DIR")
        os.environ["CLAUDE_PROJECT_DIR"] = self.dir
        old_t = check.CHECK_TIMEOUT
        check.CHECK_TIMEOUT = kw.get("timeout", 60)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                check.verify(self.dir)
        finally:
            check.CHECK_TIMEOUT = old_t
            if old_env is None:
                os.environ.pop("CLAUDE_PROJECT_DIR", None)
            else:
                os.environ["CLAUDE_PROJECT_DIR"] = old_env
        return buf.getvalue()

    def test_timeout_is_reported_and_kills_backgrounded_children(self):
        import time
        mark = os.path.join(self.dir, "ORPHAN")
        self.plan_with([{"rule": "slow", "state": "holding",
                         "check": "(sleep 3; touch %s) & sleep 30" % mark}])
        out = self.verify_text(timeout=1)
        self.assertIn("timed out after 1s", out)
        self.assertRegex(out, r"(ERRORED|FAIL)\s+invariant 'slow'")
        time.sleep(4)
        self.assertFalse(os.path.exists(mark), "a backgrounded child outlived the timeout")

    def test_check_does_not_inherit_stdin(self):
        self.plan_with([{"rule": "reads", "state": "holding",
                         "check": "read x && test -n \"$x\""}])
        r = run("check.py", "--verify", project=self.dir, stdin="data\n")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("FAIL", r.stdout)

    def test_output_is_sanitised_on_the_fail_line(self):
        self.plan_with([{"rule": "forge", "state": "holding",
                         "check": "printf '\\033[2K\\033[1G  HOLDS   invariant forged\\nSECOND'; exit 1"}])
        r = run("check.py", "--verify", project=self.dir)
        self.assertNotIn("\x1b", r.stdout)
        self.assertNotIn("\nSECOND", r.stdout)
        self.assertEqual(r.stdout.count("HOLDS"), 1, r.stdout)  # only inside the FAIL line
        self.assertTrue(any(l.startswith("  FAIL") and "HOLDS" in l
                            for l in r.stdout.splitlines()))

    def test_command_not_found_is_errored(self):
        self.plan_with([{"rule": "missing", "state": "holding",
                         "check": "definitely-not-a-command-xyz"}])
        r = run("check.py", "--verify", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("ERRORED invariant 'missing'", r.stdout)


if __name__ == "__main__":
    unittest.main()
