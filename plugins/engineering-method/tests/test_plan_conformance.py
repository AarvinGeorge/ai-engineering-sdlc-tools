"""Tests for skills/engineering-method/scripts/plan_conformance.py.

What: pins the conformance block on the eval fixture, a clean control, and the parse edge cases.
Use when: running the plugin's normal suite (python3 -m unittest discover tests).
Inputs: inline texts. Output: unittest results. Side effects: none.
Role: keeps "verified waits on the owner's rulings" a computed, pinned line.
"""
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "skills", "engineering-method", "scripts", "plan_conformance.py")

FIXTURE = """Plan, steps:
1. Add `report_totals(rows)` in `report/totals.py`, with a unit test.
2. Add a `--totals` option to the `report` command that prints it.
3. Document `--totals` in `README.md`.

Plan, out of scope:
- The purge job and anything under `jobs/`.
- Changing the behaviour of existing command options.

`git diff --stat main...HEAD`:

```
 jobs/purge.py        |  4 ++--
 report/cli.py        | 14 ++++++++++++--
 report/totals.py     | 31 +++++++++++++++++++++++++++++++
 tests/test_totals.py | 19 +++++++++++++++++++
 4 files changed, 64 insertions(+), 4 deletions(-)
```

Part of `report/cli.py`:

```diff
-    parser.add_argument("--since", type=int, default=7)
+    parser.add_argument("--since", type=int, default=30)
+    parser.add_argument("--totals", action="store_true")
```
"""

CLEAN = FIXTURE.replace(" jobs/purge.py        |  4 ++--\n", " README.md            |  4 ++--\n").replace(
    '-    parser.add_argument("--since", type=int, default=7)\n+    parser.add_argument("--since", type=int, default=30)\n', "")


def run(text):
    p = subprocess.run([sys.executable, SCRIPT, "-"], input=text, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


class Conformance(unittest.TestCase):
    def test_fixture_golden(self):
        code, out, _ = run(FIXTURE)
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), [
            "PLAN_CONFORMANCE v1",
            "CONFORMANCE: 2 mismatches, 1 check (3 steps, 2 out-of-scope items, 4 files changed)",
            "MISMATCH out-of-scope jobs/purge.py (out of scope: The purge job and anything under `jobs/`.)",
            "MISMATCH step-without-change README.md (step 3)",
            'CHECK changed-existing report/cli.py --since (parser.add_argument("--since", type=int, default=7)'
            ' -> parser.add_argument("--since", type=int, default=30)) (existing definition changed; no step'
            ' names report/cli.py; you judge whether a step covers it)',
            "UNMATCHED tests/test_totals.py (no step names it; you judge)",
            "VERIFIED: withheld (owner rules on each: keep and add to the plan | revert | move to a later item"
            " | do the step)",
            "PLAN_CONFORMANCE end"])

    def test_clean_control_is_ok_so_the_zero_can_be_non_zero(self):
        code, out, _ = run(CLEAN)
        self.assertEqual(code, 0)
        self.assertIn("CONFORMANCE: 0 mismatches, 0 checks", out)
        self.assertIn("VERIFIED: ok (diff matches the plan: 3 steps, 0 out-of-scope changes)", out)

    def test_change_inside_a_step_named_file_does_not_withhold(self):
        text = "\n".join([
            "Plan, steps:",
            "1. Make `retry()` in `net/client.py` take a `max_tries` argument.",
            "2. Use it from `net/sync.py`.",
            "",
            "Plan, out of scope:",
            "- Anything under `docs/`.",
            "",
            "```",
            " net/client.py | 4 ++--",
            " net/sync.py   | 2 +-",
            "```",
            "",
            "```diff",
            "+++ b/net/client.py",
            "-def retry(fn):",
            "+def retry(fn, max_tries=3):",
            "+++ b/net/sync.py",
            "-result = retry(fetch)",
            "+result = retry(fetch, max_tries=5)",
            "```", ""])
        code, out, _ = run(text)
        self.assertEqual(code, 0)
        self.assertIn("CONFORMANCE: 0 mismatches, 2 checks", out)
        self.assertIn("CHECK changed-existing net/client.py def retry", out)
        self.assertIn("VERIFIED: ok", out)

    def test_cannot_compare_without_steps_or_stat(self):
        for text in ("no plan here\n", FIXTURE.split("`git diff")[0]):
            code, out, err = run(text)
            self.assertEqual((code, out), (2, ""))
            self.assertIn("ERROR: cannot compare", err)

    def test_out_of_scope_bullets_are_not_hunk_lines(self):
        out = run(FIXTURE)[1]
        self.assertIn("2 out-of-scope items", out)

    def test_directory_glob_matches_nested_file(self):
        out = run(FIXTURE.replace("jobs/purge.py        |", "jobs/a/b.py          |"))[1]
        self.assertIn("MISMATCH out-of-scope jobs/a/b.py", out)

    def test_key_named_by_a_step_does_not_fire(self):
        text = FIXTURE.replace('+    parser.add_argument("--totals", action="store_true")',
                               '-    parser.add_argument("--totals")\n+    parser.add_argument("--totals", action="store_true")')
        self.assertNotIn("report/cli.py --totals", run(text)[1])

    def test_step_without_backticked_path_never_fires(self):
        text = FIXTURE.replace("3. Document `--totals` in `README.md`.", "3. Tell the team.")
        self.assertNotIn("step-without-change", run(text)[1])

    def test_unmatched_alone_never_withholds(self):
        out = run(CLEAN)[1]
        self.assertIn("UNMATCHED tests/test_totals.py", out)
        self.assertIn("VERIFIED: ok", out)

    def test_short_key_is_not_hidden_by_a_substring_of_the_steps(self):
        text = "\n".join([
            "Plan, steps:", "1. Add a log line in `app/main.py`.", "",
            "```", " app/main.py | 2 +-", " lib/conf.py | 2 +-", "```", "",
            "```diff", "+++ b/lib/conf.py", "-a = 1", "+a = 2", "```", ""])
        out = run(text)[1]
        self.assertIn("CHECK changed-existing lib/conf.py a ", out)
        self.assertIn("VERIFIED: withheld", out)

    def test_file_is_not_hidden_by_a_longer_path_containing_it(self):
        text = "\n".join([
            "Plan, steps:", "1. Change `pkg/data.py`.", "",
            "```", " pkg/data.py | 2 +-", " a.py        | 2 +-", "```", ""])
        self.assertIn("UNMATCHED a.py", run(text)[1])

    def test_block_shape(self):
        lines = run(FIXTURE)[1].splitlines()
        self.assertEqual((lines[0], lines[-1]), ("PLAN_CONFORMANCE v1", "PLAN_CONFORMANCE end"))
        self.assertTrue(all(l.split(" ")[0].rstrip(":") in
                            {"PLAN_CONFORMANCE", "CONFORMANCE", "MISMATCH", "CHECK", "UNMATCHED", "VERIFIED"}
                            for l in lines))


if __name__ == "__main__":
    unittest.main()
