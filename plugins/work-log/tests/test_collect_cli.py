import os, sys, json, subprocess, tempfile, shutil, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
SCRIPTS = os.path.join(PLUGIN, "scripts")
sys.path.insert(0, SCRIPTS); sys.path.insert(0, HERE)
import fixtures as F
COLLECT = os.path.join(SCRIPTS, "collect.py")

def run(*args, projects, cwd=None):
    return subprocess.run([sys.executable, COLLECT, "--projects-dir", projects, "--tz", "UTC", *args],
                          capture_output=True, text=True, cwd=cwd)

class CLI(unittest.TestCase):
    def setUp(self):
        # realpath: on macOS mkdtemp gives /var/... but a child's getcwd() gives /private/var/...
        self.p = os.path.realpath(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.p)
        self.w = os.path.realpath(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.w)
        self.alpha = os.path.join(self.w, "alpha-app"); os.makedirs(os.path.join(self.alpha, "src"))
        self.beta = os.path.join(self.w, "beta-site"); os.makedirs(self.beta)
        F.session(self.p, "a", "s1", self.alpha,
                  ["2026-10-26T10:00:00Z", "2026-10-26T10:05:00Z", "2026-10-26T10:10:00Z"], title="Login page")
        F.session(self.p, "b", "s2", os.path.join(self.alpha, "src"),     # subfolder counts
                  ["2026-10-27T09:00:00Z", "2026-10-27T09:12:00Z"])
        F.session(self.p, "c", "s3", self.beta, ["2026-10-26T12:00:00Z", "2026-10-26T12:10:00Z"])

    def ok(self, r):
        self.assertEqual(r.returncode, 0, r.stderr); return json.loads(r.stdout)

    def test_default_scope_is_cwd_and_below(self):
        out = self.ok(run("--start", "2026-10-26", "--end", "2026-11-01", "--no-git", projects=self.p, cwd=self.alpha))
        self.assertEqual(sorted(s["session_id"] for s in out["sessions"]), ["s1", "s2"])
        self.assertEqual(out["day_totals"], {"2026-10-26": 10.0, "2026-10-27": 12.0})
        s1 = [s for s in out["sessions"] if s["session_id"] == "s1"][0]
        self.assertEqual((s1["start"], s1["end"], s1["title"]), ("10:00", "10:10", "Login page"))
        self.assertEqual(s1["requests"], ["build the login page"])

    def test_all_projects(self):
        out = self.ok(run("--all", "--start", "2026-10-26", "--end", "2026-11-01", "--no-git", projects=self.p))
        self.assertEqual(len(out["sessions"]), 3)
        self.assertEqual(out["scope"], "all")

    def test_sibling_prefix_not_matched(self):
        F.session(self.p, "d", "s4", self.alpha + "-old", ["2026-10-26T13:00:00Z", "2026-10-26T13:05:00Z"])
        out = self.ok(run("--scope", self.alpha, "--start", "2026-10-26", "--end", "2026-11-01", "--no-git", projects=self.p))
        self.assertNotIn("s4", [s["session_id"] for s in out["sessions"]])

    def test_worktree_session_counts_by_first_cwd(self):
        later = F.line("user", "2026-10-28T10:05:00Z", "/elsewhere/wt", "s5", "next")
        F.session(self.p, "e", "s5", self.alpha, ["2026-10-28T10:00:00Z"], extra_lines=[later])
        out = self.ok(run("--scope", self.alpha, "--start", "2026-10-28", "--end", "2026-10-28", "--no-git", projects=self.p))
        self.assertEqual([s["session_id"] for s in out["sessions"]], ["s5"])

    def test_zero_fails_loud_with_counts(self):
        r = run("--scope", self.alpha, "--start", "2026-09-01", "--end", "2026-09-07", "--no-git", projects=self.p)
        self.assertEqual(r.returncode, 2); self.assertEqual(r.stdout, "")
        err = json.loads(r.stderr)
        self.assertEqual(err["sessions_in_scope_any_date"], 2)   # proves the matcher can hit
        self.assertEqual(err["files_read"], 3)

    def test_no_transcripts(self):
        empty = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, empty)
        r = run("--all", "--start", "2026-10-26", "--end", "2026-10-26", projects=empty)
        self.assertEqual(r.returncode, 2); self.assertIn("no transcripts", r.stderr)

    def test_unknown_types_skipped_and_counted(self):
        F.session(self.p, "f", "s6", self.alpha, ["2026-10-29T10:00:00Z", "2026-10-29T10:01:00Z"],
                  extra_lines=[{"type": "brand-new-thing", "sessionId": "s6"}])
        out = self.ok(run("--scope", self.alpha, "--start", "2026-10-29", "--end", "2026-10-29", "--no-git", projects=self.p))
        self.assertEqual(out["read"]["skipped_types"].get("brand-new-thing"), 1)

    def test_missing_timestamp_is_format_change(self):
        bad = {"type": "assistant", "cwd": self.alpha, "sessionId": "s7", "message": {"content": []}}
        F.session(self.p, "g", "s7", self.alpha, ["2026-10-29T10:00:00Z"], extra_lines=[bad])
        r = run("--scope", self.alpha, "--start", "2026-10-29", "--end", "2026-10-29", "--no-git", projects=self.p)
        self.assertEqual(r.returncode, 3); self.assertIn("missing timestamp", r.stderr)

    def test_bad_json_mid_file_fails_last_line_tolerated(self):
        F.session(self.p, "h", "s8", self.alpha, ["2026-10-30T10:00:00Z", "2026-10-30T10:02:00Z"], extra_lines=['{"type": "user", "trunc'])
        out = self.ok(run("--scope", self.alpha, "--start", "2026-10-30", "--end", "2026-10-30", "--no-git", projects=self.p))
        self.assertEqual(out["read"]["partial_last_lines"], 1)
        F.session(self.p, "i", "s9", self.alpha, ["2026-10-30T10:00:00Z"], extra_lines=['not json', F.line("assistant", "2026-10-30T10:01:00Z", self.alpha, "s9")])
        r = run("--scope", self.alpha, "--start", "2026-10-30", "--end", "2026-10-30", "--no-git", projects=self.p)
        self.assertEqual(r.returncode, 3); self.assertIn("not JSON", r.stderr)

    def test_subagent_files_not_read(self):
        sub = os.path.join(self.p, "a", "s1", "subagents"); os.makedirs(sub)
        F.session(os.path.join(self.p, "a", "s1"), "subagents", "agent-x", self.alpha,
                  ["2026-10-26T10:00:00Z", "2026-10-26T10:14:00Z"])
        out = self.ok(run("--scope", self.alpha, "--start", "2026-10-26", "--end", "2026-10-26", "--no-git", projects=self.p))
        self.assertEqual(out["day_totals"], {"2026-10-26": 10.0})

    def test_weekly_run_marker_excluded(self):
        F.session(self.p, "j", "s10", self.alpha, ["2026-10-31T09:00:00Z", "2026-10-31T09:10:00Z"],
                  first_prompt="[work-log weekly run] make last week's log")
        r = run("--scope", self.alpha, "--start", "2026-10-31", "--end", "2026-10-31", "--no-git", projects=self.p)
        self.assertEqual(r.returncode, 2)   # the only session that day is the logging run itself

    def test_period_clip_and_tz(self):
        # 23:50-00:10 New York local spans two local days; only the 27th is asked for
        F.session(self.p, "k", "s11", self.beta, ["2026-10-28T03:50:00Z", "2026-10-28T04:00:00Z", "2026-10-28T04:10:00Z"])
        r = subprocess.run([sys.executable, COLLECT, "--projects-dir", self.p, "--tz", "America/New_York",
                            "--scope", self.beta, "--start", "2026-10-28", "--end", "2026-10-28", "--no-git"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["day_totals"], {"2026-10-28": 10.0})
        self.assertEqual(out["tz"], "America/New_York")

    def test_git_commits_in_period_without_hashes(self):
        subprocess.run(["git", "init", "-q", self.alpha], check=True)
        env = dict(os.environ, GIT_AUTHOR_DATE="2026-10-26T11:20:00+00:00", GIT_COMMITTER_DATE="2026-10-26T11:20:00+00:00")
        for k, v in (("user.email", "dev@example.invalid"), ("user.name", "Dev")):
            subprocess.run(["git", "-C", self.alpha, "config", k, v], check=True)
        subprocess.run(["git", "-C", self.alpha, "commit", "-q", "--allow-empty", "-m", "Add login form"], check=True, env=env)
        out = self.ok(run("--scope", self.alpha, "--start", "2026-10-26", "--end", "2026-11-01", projects=self.p))
        self.assertEqual([c["subject"] for c in out["commits"]], ["Add login form"])
        self.assertNotIn("hash", json.dumps(out["commits"]))

    def test_git_commit_with_committer_date_before_author_date(self):
        subprocess.run(["git", "init", "-q", self.alpha], check=True)
        env = dict(os.environ, GIT_AUTHOR_DATE="2026-10-26T11:20:00+00:00", GIT_COMMITTER_DATE="2026-10-24T11:20:00+00:00")
        for k, v in (("user.email", "dev@example.invalid"), ("user.name", "Dev")):
            subprocess.run(["git", "-C", self.alpha, "config", k, v], check=True)
        subprocess.run(["git", "-C", self.alpha, "commit", "-q", "--allow-empty", "-m", "Skewed clock"], check=True, env=env)
        out = self.ok(run("--scope", self.alpha, "--start", "2026-10-26", "--end", "2026-11-01", projects=self.p))
        self.assertEqual([c["subject"] for c in out["commits"]], ["Skewed clock"])

    # --- added beyond the brief's list ---

    def test_symlinked_scope_matches_real_path(self):
        link = os.path.join(self.w, "alpha-link"); os.symlink(self.alpha, link)
        out = self.ok(run("--scope", link, "--start", "2026-10-26", "--end", "2026-11-01", "--no-git", projects=self.p))
        self.assertEqual(sorted(s["session_id"] for s in out["sessions"]), ["s1", "s2"])
        self.assertEqual(out["scope"], [self.alpha])

    def test_bad_tz_is_exit_3(self):
        r = run("--all", "--tz", "Not/AZone", "--start", "2026-10-26", "--end", "2026-10-26", "--no-git", projects=self.p)
        self.assertEqual(r.returncode, 3); self.assertEqual(r.stdout, "")
        self.assertIn("unknown time zone", r.stderr)

    def test_bad_arguments_are_exit_3_not_2(self):
        r = run("--all", "--scope", self.alpha, "--start", "2026-10-26", "--end", "2026-10-26", projects=self.p)
        self.assertEqual(r.returncode, 3)
        r = run("--all", "--start", "2026-10-27", "--end", "2026-10-26", projects=self.p)
        self.assertEqual(r.returncode, 3)
        r = run("--all", "--start", "last monday", "--end", "2026-10-26", projects=self.p)
        self.assertEqual(r.returncode, 3)

    def test_output_shape(self):
        out = self.ok(run("--all", "--start", "2026-10-26", "--end", "2026-11-01", "--no-git", projects=self.p))
        for k in ("version", "tz", "idle_minutes", "period", "scope", "read", "earliest_activity",
                  "sessions", "day_totals", "commits", "git_author_filter"):
            self.assertIn(k, out)
        self.assertEqual(out["earliest_activity"], "2026-10-26")
        self.assertEqual(out["read"]["files"], 3)
        s3 = [s for s in out["sessions"] if s["session_id"] == "s3"][0]
        self.assertEqual((s3["project"], s3["first_cwd"], s3["title"]), ("Beta site", self.beta, None))

    def test_overlap_split_between_sessions(self):
        F.session(self.p, "o", "s12", self.beta, ["2026-10-26T10:00:00Z", "2026-10-26T10:10:00Z"])
        out = self.ok(run("--all", "--start", "2026-10-26", "--end", "2026-10-26", "--no-git", projects=self.p))
        by = {s["session_id"]: s["active_minutes"] for s in out["sessions"]}
        self.assertEqual((by["s1"], by["s12"]), (5.0, 5.0))
        self.assertEqual(out["day_totals"], {"2026-10-26": 20.0})   # 10 overlapped + 10 for s3

    # --- fix round 1 ---

    def _repo(self, email="dev@example.invalid"):
        subprocess.run(["git", "init", "-q", self.alpha], check=True)
        for k, v in (("user.email", email), ("user.name", "Dev"), ("commit.gpgsign", "false")):
            subprocess.run(["git", "-C", self.alpha, "config", k, v], check=True)

    def _commit(self, msg, authored, committed=None, email="dev@example.invalid"):
        env = dict(os.environ, GIT_AUTHOR_DATE=authored, GIT_COMMITTER_DATE=committed or authored,
                   GIT_AUTHOR_EMAIL=email, GIT_COMMITTER_EMAIL=email)
        subprocess.run(["git", "-C", self.alpha, "commit", "-q", "--allow-empty", "-m", msg], check=True, env=env)

    def test_author_filter_is_anchored(self):
        self._repo()
        self._commit("mine", "2026-10-26T11:00:00+00:00")
        self._commit("prefix lookalike", "2026-10-26T11:05:00+00:00", email="xdev@example.invalid")
        self._commit("dot lookalike", "2026-10-26T11:10:00+00:00", email="dev@exampleXinvalid")
        self._commit("plus address", "2026-10-26T11:15:00+00:00", email="dev+wl@example.invalid")
        out = self.ok(run("--scope", self.alpha, "--start", "2026-10-26", "--end", "2026-11-01", projects=self.p))
        self.assertEqual([c["subject"] for c in out["commits"]], ["mine"])
        self.assertTrue(out["git_author_filter"])
        subprocess.run(["git", "-C", self.alpha, "config", "user.email", "dev+wl@example.invalid"], check=True)
        out = self.ok(run("--scope", self.alpha, "--start", "2026-10-26", "--end", "2026-11-01", projects=self.p))
        self.assertEqual([c["subject"] for c in out["commits"]], ["plus address"])

    def test_commit_period_uses_author_date(self):
        self._repo()
        self._commit("authored before, committed inside", "2026-10-25T12:00:00+00:00", "2026-10-26T12:00:00+00:00")
        self._commit("authored inside, committed after", "2026-10-27T12:00:00+00:00", "2026-11-03T12:00:00+00:00")
        out = self.ok(run("--scope", self.alpha, "--start", "2026-10-26", "--end", "2026-10-27", projects=self.p))
        self.assertEqual([(c["subject"], c["date"], c["time"]) for c in out["commits"]],
                         [("authored inside, committed after", "2026-10-27", "12:00")])

    def test_zero_reports_marker_exclusions(self):
        F.session(self.p, "j", "s10", self.alpha, ["2026-10-31T09:00:00Z", "2026-10-31T09:10:00Z"],
                  first_prompt="[work-log weekly run] make last week's log")
        r = run("--scope", self.alpha, "--start", "2026-10-31", "--end", "2026-10-31", "--no-git", projects=self.p)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(json.loads(r.stderr)["excluded_by_marker"], 1)

    def test_request_only_day_emitted_with_zero(self):
        F.session(self.p, "q", "s13", self.beta, ["2026-10-29T08:00:00Z"], first_prompt="check the build")
        out = self.ok(run("--scope", self.beta, "--start", "2026-10-29", "--end", "2026-10-29", "--no-git", projects=self.p))
        self.assertEqual([(s["session_id"], s["active_minutes"], s["requests"]) for s in out["sessions"]],
                         [("s13", 0.0, ["check the build"])])


if __name__ == "__main__":
    unittest.main()


class ScopeName(unittest.TestCase):
    setUp = CLI.setUp
    ok = CLI.ok

    def test_default_scope_name_is_cwd_project(self):
        out = self.ok(run("--start", "2026-10-26", "--end", "2026-11-01", "--no-git", projects=self.p, cwd=self.alpha))
        self.assertEqual(out["scope_name"], "Alpha app")

    def test_all_scope_name(self):
        out = self.ok(run("--all", "--start", "2026-10-26", "--end", "2026-11-01", "--no-git", projects=self.p))
        self.assertEqual(out["scope_name"], "All projects")

    def test_several_scopes_joined_in_order(self):
        out = self.ok(run("--scope", self.beta, "--scope", self.alpha, "--start", "2026-10-26", "--end", "2026-11-01",
                          "--no-git", projects=self.p))
        self.assertEqual(out["scope_name"], "Beta site + Alpha app")

    def test_scope_name_uses_projects_map(self):
        m = os.path.join(self.w, "map.json")
        with open(m, "w") as fh:
            json.dump({self.alpha: "Alpha product"}, fh)
        out = self.ok(run("--scope", self.alpha, "--projects-map", m, "--start", "2026-10-26", "--end", "2026-11-01",
                          "--no-git", projects=self.p))
        self.assertEqual(out["scope_name"], "Alpha product")

    def test_scope_name_in_zero_stderr(self):
        r = run("--scope", self.alpha, "--start", "2026-09-01", "--end", "2026-09-07", "--no-git", projects=self.p)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(json.loads(r.stderr)["scope_name"], "Alpha app")
