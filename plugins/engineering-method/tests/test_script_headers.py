"""Checks the six header labels on the skill's scripts.

What: every module docstring and every function or class docstring in
skills/engineering-method/scripts/*.py carries What:, Use when:, Inputs:, Output:,
Side effects: and Role: (a function's labels may share lines).
Use when: running the plugin's normal suite (python3 -m unittest discover tests).
Inputs: the script files. Output: unittest results. Side effects: none.
Role: principle 7's header rule as a check, for the code this release adds.
"""
import ast
import glob
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = sorted(glob.glob(os.path.join(os.path.dirname(HERE), "skills", "engineering-method", "scripts", "*.py")))
LABELS = ("What:", "Use when:", "Inputs:", "Output", "Side effects:", "Role:")


class Headers(unittest.TestCase):
    def test_three_scripts_exist(self):
        names = {os.path.basename(p) for p in SCRIPTS}
        self.assertTrue({"eval_stats.py", "plan_conformance.py", "permissions_check.py"} <= names, names)

    def test_every_definition_has_the_labels(self):
        for path in SCRIPTS:
            tree = ast.parse(open(path, encoding="utf-8").read())
            nodes = [tree] + [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
            for n in nodes:
                doc = ast.get_docstring(n) or ""
                missing = [l for l in LABELS if l not in doc]
                self.assertFalse(missing, "%s %s lacks %s" % (os.path.basename(path), getattr(n, "name", "module"), missing))


if __name__ == "__main__":
    unittest.main()
