import os, sys, json, subprocess, tempfile, shutil, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
SCRIPTS = os.path.join(PLUGIN, "scripts")
sys.path.insert(0, SCRIPTS); sys.path.insert(0, HERE)
SCAN = os.path.join(SCRIPTS, "scan.py")

def entries(summary, style="hr", **meta):
    m = {"scope_name": "Alpha app", "period_start": "2026-10-26", "period_end": "2026-11-01",
         "kind": "request", "style": style, "notes": []}; m.update(meta)
    return {"meta": m, "entries": [{"id": "E1", "date": "2026-10-26", "start": "10:00", "end": "10:30",
                                    "minutes": 30, "project": "Alpha app", "type": "Claude session", "summary": summary}]}

class Scan(unittest.TestCase):
    def run_scan(self, data, never=None):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d)
        p = os.path.join(d, "e.json"); json.dump(data, open(p, "w"))
        args = [sys.executable, SCAN, p]
        if never is not None:
            n = os.path.join(d, "never.txt"); open(n, "w").write(never); args += ["--never", n]
        env = dict(os.environ, HOME=d)   # never read the real ~/.config
        return subprocess.run(args, capture_output=True, text=True, env=env)

    def hit(self, summary, rule, **kw):
        r = self.run_scan(entries(summary, **kw))
        self.assertEqual(r.returncode, 1, r.stdout); self.assertIn(rule, r.stdout)
        return r

    def test_clean(self):
        r = self.run_scan(entries("Built the sign-in page so staff can log in without help."))
        self.assertEqual(r.returncode, 0, r.stdout); self.assertIn("clean", r.stdout)

    def test_email_hidden(self):
        r = self.hit("Sent notes to jo@example.com about the launch.", "email")
        self.assertNotIn("jo@example.com", r.stdout + r.stderr)
    def test_phone(self): self.hit("Called +1 (412) 555-0199 to confirm.", "phone")
    def test_short_number_not_phone(self):
        self.assertEqual(self.run_scan(entries("Fixed 3 bugs in 2 hours.")).returncode, 0)
    def test_keys(self):
        for k in ["sk-ant-abcdefghijklmnop1234", "AKIAABCDEFGHIJKLMNOP", "ghp_" + "a1" * 12,
                  "xoxb-1234567890-abc", "-----BEGIN PRIVATE KEY", "Zx9" * 12]:
            r = self.hit("Rotated " + k, "key-like")
            self.assertNotIn(k, r.stdout + r.stderr)
    def test_never_list_whole_word_case_insensitive(self):
        r = self.run_scan(entries("Met Jordan Example about pricing."), never="# names\njordan example\n")
        self.assertEqual(r.returncode, 1); self.assertNotIn("Jordan", r.stdout)
        self.assertIn("never-list", r.stdout)
        self.assertEqual(self.run_scan(entries("Met the team."), never="jordan example\n").returncode, 0)
    def test_never_list_whole_word_only(self):
        self.assertEqual(self.run_scan(entries("Met the Jordanian team."), never="jordan\n").returncode, 0)
    def test_over_30_words_both_styles(self):
        long = " ".join(["word"] * 31)
        self.hit(long, "over-30-words"); self.hit(long, "over-30-words", style="detailed")
        self.assertEqual(self.run_scan(entries(" ".join(["word"] * 30))).returncode, 0)
    def test_hr_codes(self):
        self.hit("Updated plan/plan.json for the release.", "file-path")
        self.hit("Fixed the bug in collect.py.", "file-path")
        self.hit("Merged a1b2c3d into the main line.", "commit-hash")
        self.hit("Worked on feat/login-page.", "branch-name")
        self.hit("Ran `pytest` on the code.", "code-mark")
        self.hit("Wrote doc 133 and closed #42.", "internal-code")
        self.hit("Shipped version v0.1.0.", "internal-code")
        self.hit("Set up the SSO and SCIM flow.", "abbreviation")
    def test_detailed_allows_technical_names(self):
        self.assertEqual(self.run_scan(entries("Fixed collect.py on feat/login.", style="detailed")).returncode, 0)
    def test_allowed_abbreviations(self):
        self.assertEqual(self.run_scan(entries("Prepared the AI summary for HR.")).returncode, 0)
    def test_scope_name_scanned(self):
        r = self.run_scan(entries("Fine.", scope_name="ops@example.com"))
        self.assertEqual(r.returncode, 1); self.assertIn("entry meta", r.stdout)
        self.assertNotIn("ops@example.com", r.stdout)
    def test_notes_scanned(self):
        r = self.run_scan(entries("Fine.", notes=["mail jo@example.com"]))
        self.assertEqual(r.returncode, 1); self.assertIn("entry meta", r.stdout)
    def test_project_scanned(self):
        d = entries("Fine."); d["entries"][0]["project"] = "ops@example.com"
        r = self.run_scan(d); self.assertEqual(r.returncode, 1); self.assertIn("field project", r.stdout)
    def test_empty_summary(self): self.hit("", "empty-summary")
    def test_bad_input_exit_3(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d); p = os.path.join(d, "x.json"); open(p, "w").write("{")
        self.assertEqual(subprocess.run([sys.executable, SCAN, p], capture_output=True).returncode, 3)
