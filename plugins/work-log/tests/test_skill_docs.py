import os, sys, json, subprocess, tempfile, shutil, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
SCRIPTS = os.path.join(PLUGIN, "scripts")
sys.path.insert(0, SCRIPTS); sys.path.insert(0, HERE)
import re
SK = os.path.join(PLUGIN, "skills", "work-log")
def read(*p): return open(os.path.join(*p)).read()

class Docs(unittest.TestCase):
    def test_frontmatter(self):
        s = read(SK, "SKILL.md"); m = re.match(r"---\n(.*?)\n---\n", s, re.S)
        self.assertTrue(m); fm = m.group(1)
        self.assertIn("name: work-log", fm)
        desc = re.search(r"description: (.*)", fm).group(1)
        self.assertLessEqual(len(desc), 1024)
    def test_scripts_referenced_exist(self):
        s = read(SK, "SKILL.md")
        for name in set(re.findall(r"scripts/(\w+\.py)", s)):
            self.assertTrue(os.path.exists(os.path.join(SCRIPTS, name)), name)
    def test_schedule_marker_matches_collect_default(self):
        import collect
        self.assertIn(collect.DEFAULT_MARKER, read(SK, "references", "schedule.md"))
        self.assertIn(collect.DEFAULT_MARKER, read(SK, "SKILL.md"))
    def test_evals_shape(self):
        ev = os.path.join(PLUGIN, "evals"); cases = sorted(os.listdir(ev))
        self.assertEqual(len(cases), 4)
        for c in cases:
            for f in ("prompt.md", "graders/criteria.md", "graders/skill-fired.md"):
                self.assertTrue(os.path.exists(os.path.join(ev, c, f)), c + "/" + f)
    def test_no_real_identifiers(self):
        bad = re.compile(r"/Users/|@gmail\.com", re.I)
        for root, _, files in os.walk(PLUGIN):
            if "/.claude-plugin" in root or "__pycache__" in root or ".pytest_cache" in root: continue
            for f in files:
                if f == "test_skill_docs.py": continue   # holds the pattern itself
                txt = open(os.path.join(root, f), errors="ignore").read()
                self.assertIsNone(bad.search(txt), os.path.join(root, f))
