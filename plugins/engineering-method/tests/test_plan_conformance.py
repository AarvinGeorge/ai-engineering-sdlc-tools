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

    def test_headerless_hunk_goes_to_the_whole_name_match(self):
        text = "\n".join([
            "Plan, steps:", "1. Add a `--totals` option in `cli.py`.", "",
            "```", " cli.py        | 3 +++", " report/cli.py | 2 +-", "```", "",
            "Part of `report/cli.py`:", "",
            "```diff",
            '-    parser.add_argument("--since", type=int, default=7)',
            '+    parser.add_argument("--since", type=int, default=30)',
            "```", ""])
        out = run(text)[1]
        self.assertIn("CHECK changed-existing report/cli.py --since", out)
        self.assertIn("VERIFIED: withheld", out)

    def test_raw_git_diff_hunks_are_read(self):
        text = "\n".join([
            "Plan, steps:", "1. Add a `--totals` option to the report command.", "",
            "Plan, out of scope:", "- Changing the behaviour of existing command options.", "",
            " report/cli.py | 3 ++-", " 1 file changed, 2 insertions(+), 1 deletion(-)", "",
            "diff --git a/report/cli.py b/report/cli.py",
            "index 1111111..2222222 100644", "--- a/report/cli.py", "+++ b/report/cli.py",
            "@@ -10,3 +10,4 @@ def build():",
            '-    parser.add_argument("--since", type=int, default=7)',
            '+    parser.add_argument("--since", type=int, default=30)',
            '+    parser.add_argument("--totals", action="store_true")', ""])
        out = run(text)[1]
        self.assertIn("1 out-of-scope item,", out)
        self.assertIn("CHECK changed-existing report/cli.py --since", out)
        self.assertIn("VERIFIED: withheld", out)

    def test_list_item_saying_step_does_not_flip_the_section(self):
        text = "\n".join([
            "Plan, steps:", "1. Add `report_totals(rows)` in `report/totals.py`.", "",
            "Plan, out of scope:", "- The deploy step.", "- The purge job and anything under `jobs/`.", "",
            "```", " jobs/purge.py    | 4 ++--", " report/totals.py | 31 +++++++", "```", ""])
        out = run(text)[1]
        self.assertIn("MISMATCH out-of-scope jobs/purge.py", out)
        self.assertIn("VERIFIED: withheld", out)

    def test_code_shaped_key_in_step_prose_covers_the_change(self):
        text = "\n".join([
            "Plan, steps:", "1. Raise MAX_TRIES to 5 in the client.", "",
            "```", " net/client.py | 2 +-", "```", "",
            "```diff", "+++ b/net/client.py", "-MAX_TRIES = 3", "+MAX_TRIES = 5", "```", ""])
        out = run(text)[1]
        self.assertIn("0 checks", out)
        self.assertIn("VERIFIED: ok", out)

    def test_singular_counts(self):
        text = "\n".join([
            "Plan, steps:", "1. Change `jobs/x.py`.", "",
            "Plan, out of scope:", "- Anything under `jobs/`.", "",
            "```", " jobs/x.py | 2 +-", "```", ""])
        self.assertIn("CONFORMANCE: 1 mismatch, 0 checks (1 step, 1 out-of-scope item, 1 file changed)",
                      run(text)[1])

    RENAME = "\n".join([
        "Plan, steps:", "1. Add `report_totals(rows)` in `report/totals.py`.", "",
        "Plan, out of scope:", "- Anything under `jobs/`.", "",
        " jobs/{purge.py => purge_all.py} | 4 ++--",
        " jobs/logo.png                   | Bin 0 -> 2048 bytes",
        " jobs/my notes.txt               | 3 +++",
        " report/totals.py                | 31 +++++++++++++++++++++++++++++++",
        " 4 files changed, 36 insertions(+), 2 deletions(-)", ""])

    def test_rename_binary_and_spaced_names_withhold(self):
        out = run(self.RENAME)[1]
        for f in ("jobs/purge.py", "jobs/purge_all.py", "jobs/logo.png"):
            self.assertIn("MISMATCH out-of-scope %s " % f, out)
        self.assertIn("UNREAD diff-stat (its summary says 4 files changed, 3 stat lines read;", out)
        self.assertIn("VERIFIED: withheld", out)

    def test_spaced_name_alone_is_unread_and_withholds(self):
        text = self.RENAME.replace(" jobs/{purge.py => purge_all.py} | 4 ++--\n", "").replace(
            " jobs/logo.png                   | Bin 0 -> 2048 bytes\n", "").replace(
            " 4 files changed", " 2 files changed").replace("`jobs/`", "`old/`")
        out = run(text)[1]
        self.assertIn("0 mismatches", out)
        self.assertIn("UNREAD diff-stat (its summary says 2 files changed, 1 stat lines read;", out)
        self.assertIn("VERIFIED: withheld", out)

    def test_summary_that_matches_the_stat_prints_no_unread(self):
        text = "\n".join(self.RENAME.splitlines()[:6] + [
            " report/totals.py | 31 +++++", " 1 file changed, 31 insertions(+)", ""])
        out = run(text)[1]
        self.assertNotIn("UNREAD", out)
        self.assertIn("VERIFIED: ok", out)

    CONTEXT = "\n".join([
        "Plan, steps:", "1. Document `--totals` in `README.md`.", "",
        "Plan, out of scope:", "- Anything under `jobs/`.", "",
        " README.md | 3 ++-", " 1 file changed, 2 insertions(+), 1 deletion(-)", "",
        "diff --git a/README.md b/README.md", "--- a/README.md", "+++ b/README.md",
        "@@ -10,6 +10,7 @@ Usage",
        " 1. Install it; see `docs/setup.md`.",
        " - Reports live in `README.md` and `report/`.",
        "-Old line", "+Run `report --totals`.",
        " * 2 | 3 pipes in a context line", ""])

    def test_hunk_context_lines_are_not_plan_text(self):
        out = run(self.CONTEXT)[1]
        self.assertIn("CONFORMANCE: 0 mismatches, 0 checks (1 step, 1 out-of-scope item, 1 file changed)", out)
        self.assertIn("VERIFIED: ok", out)

    def test_context_control_a_real_out_of_scope_change_still_withholds(self):
        text = self.CONTEXT.replace(" README.md | 3 ++-", " README.md | 3 ++-\n jobs/x.py | 1 +").replace(
            " 1 file changed", " 2 files changed")
        out = run(text)[1]
        self.assertIn("MISMATCH out-of-scope jobs/x.py", out)
        self.assertIn("VERIFIED: withheld", out)

    def test_no_argument_is_an_error_not_a_wait(self):
        # a valid plan on stdin: before this rule it was read and exit 0; now no argument is exit 2
        p = subprocess.run([sys.executable, SCRIPT], input=FIXTURE, capture_output=True, text=True, timeout=10)
        self.assertEqual((p.returncode, p.stdout), (2, ""))
        self.assertIn("ERROR: cannot compare", p.stderr)

    def test_block_shape(self):
        lines = run(FIXTURE)[1].splitlines()
        self.assertEqual((lines[0], lines[-1]), ("PLAN_CONFORMANCE v1", "PLAN_CONFORMANCE end"))
        self.assertTrue(all(l.split(" ")[0].rstrip(":") in
                            {"PLAN_CONFORMANCE", "CONFORMANCE", "MISMATCH", "CHECK", "UNMATCHED", "VERIFIED"}
                            for l in lines))


if __name__ == "__main__":
    unittest.main()
