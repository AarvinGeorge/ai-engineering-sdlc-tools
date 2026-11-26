"""Proves each new code grader in the five hybrid cases can pass and can fail.

What: scaffolds each case's workspace with its fixture.sh, runs the owning script on the
scaffolded file by path (the case's input), and checks every new regex grader (trace and
last_message) matches the real output and misses a prose-only answer; not_contains guards are
checked the other way round. Also checks the case frontmatter and file names the prompts give.
Use when: running the plugin's normal suite (python3 -m unittest discover tests).
Inputs: grader files, prompts, scaffolds, the three scripts, tests/fixtures/hybrid/prose_only.md.
Output: unittest results.
Side effects: runs fixture.sh and the scripts as subprocesses in temporary directories.
Role: a code grader that cannot be shown to pass and to fail tests nothing. Patterns are
JavaScript in the eval runner and Python here, so they use only the shared subset: no
lookbehind, no inline flags, no named groups.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
EVALS = os.path.join(PLUGIN, "evals")
SCRIPTS = os.path.join(PLUGIN, "skills", "engineering-method", "scripts")
sys.path.insert(0, HERE)
from test_plan_conformance import FIXTURE  # noqa: E402

CASES = ("eval-pass-k-floor", "eval-judge-independent-calibrated", "eval-run-accounting",
         "verified-matches-plan", "permission-profile-live")
SCAFFOLDED = {"eval-judge-independent-calibrated": "labels.csv", "eval-run-accounting": "eval-out/",
              "verified-matches-plan": "review-input.md", "permission-profile-live": "settings.json"}
# The settings file a sound answer proposes (deny kubectl delete, ask release.sh, narrow allow).
PROPOSAL = json.dumps({"permissions": {
    "allow": ["Bash(kubectl get *)", "Bash(kubectl describe *)"],
    "ask": ["Bash(./ops/release.sh *)"],
    "deny": ["Bash(kubectl delete *)", "Bash(dropdb *)"]}})
NEW_CODE_GRADER = re.compile(r"^c\d[a-z]-.*\.md$")
SHARED_SUBSET_BANNED = re.compile(r"\(\?<[=!]|\(\?[imsx]|\(\?P?<\w")


def grader(case, name):
    """What: read one grader file's frontmatter.
    Use when: every test here. Inputs: case folder name, grader file name.
    Output: dict of type, target, pattern, match, flags (None when absent).
    Side effects: reads the file. Role: plumbing."""
    text = open(os.path.join(EVALS, case, "graders", name), encoding="utf-8").read()
    front = text.split("---")[1]

    def get(key):
        m = re.search(r"^%s:\s*(.*?)\s*$" % key, front, re.M)
        if not m:
            return None
        value = m.group(1)
        if len(value) >= 2 and value[0] == value[-1] == "'":
            value = value[1:-1].replace("''", "'")
        return value
    return {"type": get("type"), "target": get("target") or "last_message",
            "pattern": get("pattern"), "match": get("match") or "contains", "flags": get("flags")}


def new_code_graders(case):
    """What: the new regex graders of one case (file names c<N><letter>-*.md).
    Use when: the proofs. Inputs: case. Output: sorted list of (name, grader dict).
    Side effects: lists the folder. Role: plumbing."""
    names = sorted(n for n in os.listdir(os.path.join(EVALS, case, "graders")) if NEW_CODE_GRADER.match(n))
    return [(n, grader(case, n)) for n in names]


def script(name, *args, cwd=None):
    """What: run one bundled script with the current interpreter.
    Use when: producing a case's real output. Inputs: script name, arguments, working dir.
    Output: stdout (fails the caller loudly if the exit code is not 0).
    Side effects: subprocess. Role: plumbing."""
    p = subprocess.run([sys.executable, os.path.join(SCRIPTS, name)] + list(args),
                       capture_output=True, text=True, cwd=cwd)
    if p.returncode != 0:
        raise AssertionError("%s %s exited %d: %s" % (name, args, p.returncode, p.stderr))
    return p.stdout


def search(g, text):
    """What: apply a grader's pattern to a text the way the runner does (flags: i only).
    Use when: every proof. Inputs: grader dict, text. Output: match object or None.
    Side effects: none. Role: plumbing."""
    return re.search(g["pattern"], text, re.I if g["flags"] == "i" else 0)


def bolded(line):
    """What: the same line with its key in Markdown bold ("VERDICT: x" -> "**VERDICT:** x").
    Use when: a pattern tolerates \\W{0,4} after the key. Inputs: matched text. Output: text.
    Side effects: none. Role: plumbing."""
    key, rest = line.split(":", 1)
    return "**%s:**%s" % (key, rest)


class Graders(unittest.TestCase):
    def scaffold(self, case):
        """What: a fresh workspace with the case's fixture.sh run in it, as --scaffold does.
        Use when: a case reads a file. Inputs: case. Output: workspace path.
        Side effects: temp dir (cleaned up), runs bash. Role: plumbing."""
        ws = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, ws)
        p = subprocess.run(["bash", os.path.join(EVALS, case, "fixture.sh")], cwd=ws,
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        return ws

    def outputs(self):
        """What: each case's real script output, run on the scaffolded file by path.
        Use when: the proofs. Inputs: none. Output: {case: [stdout, ...]} (permission has two:
        the --file and the --inline forms, since graders must not depend on which).
        Side effects: scaffolds and subprocesses. Role: plumbing."""
        cal = self.scaffold("eval-judge-independent-calibrated")
        acc = self.scaffold("eval-run-accounting")
        ver = self.scaffold("verified-matches-plan")
        perm = self.scaffold("permission-profile-live")
        with open(os.path.join(perm, "settings.json"), "w") as fh:
            fh.write(PROPOSAL)
        return {
            "eval-pass-k-floor": [script("eval_stats.py", "floor", "--name", "never quotes a refund amount",
                                         "--results", "PPF")],
            "eval-judge-independent-calibrated": [script("eval_stats.py", "calibrate", "--labels", "labels.csv",
                                                         cwd=cal)],
            "eval-run-accounting": [script("eval_stats.py", "runs", "eval-out/result.json",
                                           "--fixture", "parse-invoices=resources/", cwd=acc)],
            "verified-matches-plan": [script("plan_conformance.py", "review-input.md", cwd=ver)],
            "permission-profile-live": [
                script("permissions_check.py", "--file", "project=settings.json",
                       "--command", "kubectl delete pod x", cwd=perm),
                script("permissions_check.py", "--inline", "project=" + PROPOSAL,
                       "--command", "kubectl delete pod x")],
        }

    def test_regex_graders_pass_on_the_block_and_fail_on_prose(self):
        prose = open(os.path.join(HERE, "fixtures", "hybrid", "prose_only.md"), encoding="utf-8").read()
        checked = 0
        for case, outs in self.outputs().items():
            for name, g in new_code_graders(case):
                self.assertEqual(g["type"], "regex", (case, name))
                self.assertIsNone(SHARED_SUBSET_BANNED.search(g["pattern"]), (case, name))
                for out in outs:
                    # A trace carries the tool result JSON-encoded; last_message carries it pasted.
                    seen = json.dumps(out) if g["target"] == "trace" else out
                    if g["match"] == "not_contains":
                        self.assertIsNone(search(g, seen), (case, name))
                        ok = seen.replace("VERIFIED: withheld", "VERIFIED: ok")
                        self.assertIsNotNone(search(g, ok), (case, name))
                        self.assertIsNotNone(search(g, bolded("VERIFIED: ok")), (case, name))
                        continue
                    m = search(g, seen)
                    self.assertIsNotNone(m, (case, name, out))
                    self.assertIsNone(search(g, prose), (case, name))
                    if r"\W{0,4}" in g["pattern"]:
                        self.assertIsNotNone(search(g, bolded(m.group(0))), (case, name))
                checked += 1
        self.assertEqual(checked, 15)  # 3 + 3 + 4 + 3 + 2 new regex graders: proves the loop ran

    def test_permission_c1b_misses_other_blocks_and_the_draft(self):
        g = grader("permission-profile-live", "c1b-delete-deny-holds-across-files.md")
        for cmds in (["./ops/release.sh prod"], ["dropdb ledger"], ["kubectl get pods"],
                     ["./ops/release.sh prod", "dropdb ledger", "kubectl get pods"]):
            args = [a for c in cmds for a in ("--command", c)]
            out = script("permissions_check.py", "--inline", "project=" + PROPOSAL, *args)
            self.assertEqual(out.count("PERMISSIONS_CHECK v1"), len(cmds))
            self.assertIsNone(search(g, out), cmds)
        # release.sh and dropdb blocks do carry "LOOSENED_BY_OTHER_FILE: no", so those misses are the RULE part.
        self.assertIn("LOOSENED_BY_OTHER_FILE: no", out)
        both = script("permissions_check.py", "--inline", "project=" + PROPOSAL,
                      "--command", "./ops/release.sh prod", "--command", "kubectl delete pod x")
        self.assertIsNotNone(search(g, both))
        draft = self.scaffold("permission-profile-live")
        out = script("permissions_check.py", "--file", "project=settings.json",
                     "--command", "kubectl delete pod x", cwd=draft)
        self.assertIn("PERMISSIONS_CHECK v1", out)
        self.assertIsNone(search(g, out))  # the user's draft does not deny kubectl delete

    def test_no_new_tool_used_graders(self):
        for case in CASES:
            for name, g in new_code_graders(case):
                self.assertNotEqual(g["type"], "tool_used", (case, name))

    def test_cases_have_turns_tools_and_named_files(self):
        for case in CASES:
            prompt = open(os.path.join(EVALS, case, "prompt.md"), encoding="utf-8").read()
            front = prompt.split("---")[1]
            self.assertRegex(front, r"(?m)^max_turns: 16$", case)
            self.assertRegex(front, r"(?m)^allowed_tools: \[Read, Glob, Grep, Skill, Bash\]$", case)
            if case in SCAFFOLDED:
                self.assertIn("`%s`" % SCAFFOLDED[case], prompt, case)
                yaml = open(os.path.join(EVALS, case, "case.yaml"), encoding="utf-8").read()
                self.assertIn('schema_version: "1.1"', yaml)
                self.assertIn("name: %s\n" % case, yaml)
                self.assertIn("scaffold_script: fixture.sh", yaml)
                self.assertIn(SCAFFOLDED[case].rstrip("/"), os.listdir(self.scaffold(case)), case)

    def test_scaffolded_inputs_match_the_prompts(self):
        ver = os.path.join(EVALS, "verified-matches-plan")
        self.assertEqual(open(os.path.join(ver, "resources", "review-input.md")).read(), FIXTURE)
        self.assertIn(FIXTURE, open(os.path.join(ver, "prompt.md")).read())
        cal = os.path.join(EVALS, "eval-judge-independent-calibrated")
        csv_text = open(os.path.join(cal, "resources", "labels.csv")).read()
        self.assertEqual(len(csv_text.strip().splitlines()), 10)
        self.assertIn(csv_text, open(os.path.join(cal, "prompt.md")).read())


if __name__ == "__main__":
    unittest.main()
