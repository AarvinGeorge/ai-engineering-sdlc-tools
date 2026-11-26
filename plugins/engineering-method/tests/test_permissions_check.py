"""Tests for skills/engineering-method/scripts/permissions_check.py.

What: pins rule matching (docs' wildcard and compound-command rules), deny > ask > allow
across files, the cross-file probe, and the output contract.
Use when: running the plugin's normal suite (python3 -m unittest discover tests).
Inputs: inline settings JSON. Output: unittest results. Side effects: none.
Role: keeps settings precedence a computed fact, matching code.claude.com/docs/en/permissions.
"""
import importlib.util
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "skills", "engineering-method", "scripts", "permissions_check.py")


def load():
    spec = importlib.util.spec_from_file_location("permissions_check", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run(layers, *commands):
    args = [sys.executable, SCRIPT]
    for scope, body in layers.items():
        args += ["--inline", "%s=%s" % (scope, json.dumps(body))]
    for c in commands:
        args += ["--command", c]
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def perms(**kw):
    return {"permissions": kw}


class Matching(unittest.TestCase):
    def setUp(self):
        self.m = load().rule_matches

    def test_exact_rule(self):
        self.assertTrue(self.m("Bash(npm run build)", "npm run build"))
        self.assertFalse(self.m("Bash(npm run build)", "npm run build --watch"))

    def test_trailing_space_star_matches_bare_and_respects_space(self):
        self.assertTrue(self.m("Bash(ls *)", "ls -la"))
        self.assertTrue(self.m("Bash(ls *)", "ls"))
        self.assertFalse(self.m("Bash(ls *)", "lsof"))
        self.assertTrue(self.m("Bash(ls*)", "lsof"))

    def test_colon_star_alias_only_at_end(self):
        for c in ("ls", "ls -la"):
            self.assertEqual(self.m("Bash(ls:*)", c), self.m("Bash(ls *)", c))
        self.assertFalse(self.m("Bash(ls:*)", "lsof"))
        self.assertFalse(self.m("Bash(git:* push)", "git push"))

    def test_inner_star(self):
        self.assertTrue(self.m("Bash(* --help *)", "npm --help x"))
        self.assertFalse(self.m("Bash(* --help *)", "npm --help"))
        self.assertTrue(self.m("Bash(git log * main)", "git log -5 main"))
        self.assertFalse(self.m("Bash(git log * main)", "git log main"))

    def test_bare_bash(self):
        self.assertTrue(self.m("Bash", "anything at all"))
        self.assertTrue(self.m("Bash(*)", "anything"))
        self.assertFalse(self.m("Read", "ls"))


class Precedence(unittest.TestCase):
    def test_deny_beats_allow_in_one_file(self):
        _, out, _ = run({"project": perms(allow=["Bash(kubectl *)"], deny=["Bash(kubectl delete *)"])},
                        "kubectl delete pod x", "kubectl get pods")
        a, b = out.split("PERMISSIONS_CHECK v1")[1:]
        self.assertIn("DECISION: deny", a)
        self.assertIn("RULE: Bash(kubectl delete *) [deny] in project (inline)", a)
        self.assertIn("ALSO_MATCHED: Bash(kubectl *) [allow] in project (inline) -- not reached", a)
        self.assertIn("DECISION: allow", b)

    def test_ask_beats_more_specific_allow(self):
        _, out, _ = run({"project": perms(ask=["Bash(git *)"], allow=["Bash(git status)"])}, "git status")
        self.assertIn("DECISION: ask", out)

    def test_deny_holds_across_files_both_ways(self):
        for deny_scope, allow_scope in (("project", "user"), ("project", "local"), ("project", "cli"),
                                        ("user", "project")):
            _, out, _ = run({deny_scope: perms(deny=["Bash(rm *)"]), allow_scope: perms(allow=["Bash(rm *)"])},
                            "rm -rf x")
            self.assertIn("DECISION: deny", out, (deny_scope, allow_scope))

    def test_cross_file_probe_and_loosened_line(self):
        _, out, _ = run({"project": perms(deny=["Bash(kubectl delete *)"])}, "kubectl delete pod x")
        self.assertIn('CROSS_FILE_PROBE: allow "Bash(kubectl delete pod x)" added to user -> deny; '
                      'added to local -> deny', out)
        self.assertIn("LOOSENED_BY_OTHER_FILE: no (lists merge across managed, cli, local, project and user; "
                      "a deny in any file is checked before an allow in any file)", out)

    def test_ask_probe_wording(self):
        _, out, _ = run({"project": perms(ask=["Bash(./ops/release.sh *)"])}, "./ops/release.sh prod")
        self.assertIn("LOOSENED_BY_OTHER_FILE: no (an ask in any file is checked before an allow in any file)", out)

    def test_allow_can_decide_so_the_line_is_not_hard_coded(self):
        _, out, _ = run({"user": perms(allow=["Bash(make *)"])}, "make test")
        self.assertIn("DECISION: allow", out)
        self.assertIn("LOOSENED_BY_OTHER_FILE: n/a", out)
        _, out, _ = run({"user": perms(allow=["Bash(make *)"])}, "cargo build")
        self.assertIn("DECISION: no-rule", out)


class Compound(unittest.TestCase):
    def test_allow_needs_every_part(self):
        _, out, _ = run({"user": perms(allow=["Bash(safe *)"])}, "safe x && other")
        self.assertIn("DECISION: no-rule", out)
        self.assertIn("SUBCOMMANDS: 2", out)

    def test_deny_any_part(self):
        _, out, _ = run({"user": perms(deny=["Bash(git clean *)"], allow=["Bash(cd *)"])}, "cd /tmp && git clean -f")
        self.assertIn("DECISION: deny", out)

    def test_dangling_operator_never_allows(self):
        _, out, _ = run({"user": perms(allow=["Bash(npm test *)"])}, "npm test &&")
        self.assertIn("DECISION: no-rule", out)

    def test_quoted_separator_is_not_a_split(self):
        _, out, _ = run({"user": perms(allow=["Bash(echo *)"])}, 'echo "a && b"')
        self.assertIn("SUBCOMMANDS: 1", out)
        self.assertIn("DECISION: allow", out)


class Contract(unittest.TestCase):
    LIVE = {"permissions": {"allow": ["Bash(kubectl get *)", "Bash(kubectl describe *)"],
                            "ask": ["Bash(./ops/release.sh *)"],
                            "deny": ["Bash(kubectl delete *)", "Bash(dropdb *)"],
                            "disableBypassPermissionsMode": "disable"}}

    def test_never_prints_the_guarded_strings(self):
        _, out, _ = run({"project": self.LIVE}, "kubectl delete pod x", "dropdb prod", "kubectl get pods")
        self.assertNotIn("disablebypasspermissionsmode", out.lower())
        self.assertNotIn("Bash(ssh", out)

    def test_block_order_and_stability(self):
        args = ({"project": self.LIVE}, "kubectl delete pod x")
        out1, out2 = run(*args)[1], run(*args)[1]
        self.assertEqual(out1, out2)
        keys = [l.split(":")[0] for l in out1.splitlines()]
        self.assertEqual(keys, ["PERMISSIONS_CHECK v1", "COMMAND", "SUBCOMMANDS", "DECISION", "RULE", "ORDER",
                                "ALSO_MATCHED", "CROSS_FILE_PROBE", "LOOSENED_BY_OTHER_FILE", "TRUST", "LIMIT",
                                "NOTES", "END"])

    def test_mode_line(self):
        _, out, _ = run({"project": {"permissions": {"defaultMode": "bypassPermissions", "deny": ["Bash(rm *)"]}}},
                        "rm x")
        self.assertIn("MODE: defaultMode bypassPermissions in project -> not applied "
                      "(only user or managed settings can set it)", out)

    def test_top_level_mode_is_not_evaluated(self):
        _, out, _ = run({"project": {"defaultMode": "bypassPermissions", "permissions": {"deny": ["Bash(rm *)"]}}},
                        "rm x")
        self.assertIn("MODE: bypassPermissions (top-level key, not documented; not evaluated)", out)
        self.assertNotIn("not applied", out)

    def test_help_and_unknown_args(self):
        p = subprocess.run([sys.executable, SCRIPT, "--help"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        self.assertIn("--command", p.stdout)
        p = subprocess.run([sys.executable, SCRIPT, "--bogus"], capture_output=True, text=True)
        self.assertEqual((p.returncode, p.stdout), (2, ""))
        self.assertIn("ERROR:", p.stderr)

    def test_many_stars_do_not_hang(self):
        spec = "Bash(" + "*a" * 14 + "*b)"
        p = subprocess.run([sys.executable, SCRIPT, "--inline", json.dumps({"permissions": {"deny": [spec]}}).join(["project=", ""]),
                            "--command", "a" * 40], capture_output=True, text=True, timeout=1)
        self.assertEqual(p.returncode, 0)
        self.assertIn("DECISION: no-rule", p.stdout)

    def test_bad_input_exit_2(self):
        for args in (["--inline", "project={bad"], ["--inline", "nowhere={}", "--command", "x"],
                     ["--inline", "project={}"], ["--inline", 'project={"permissions":{"deny":[1]}}', "--command", "x"]):
            p = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)
            self.assertEqual((p.returncode, p.stdout), (2, ""), args)
            self.assertIn("ERROR:", p.stderr)


class Undocumented(unittest.TestCase):
    """Cases the docs leave open (H1-H4) or name only for deny and ask: never print allow."""

    def test_substitution_never_allows(self):
        for c in ("echo $(rm -rf x)", "echo `rm -rf x`", "(rm -rf x)", "echo $(unclosed"):
            _, out, _ = run({"user": perms(allow=["Bash(echo *)", "Bash((rm *)"])}, c)
            self.assertNotIn("DECISION: allow", out, c)

    def test_deny_reaches_nested_bodies(self):
        for c in ('echo "$(git clean -f)"', "echo `git clean -f`", "(cd /tmp; git clean -f)",
                  "for f in a; do git clean -f; done"):
            _, out, _ = run({"user": perms(deny=["Bash(git clean *)"], allow=["Bash(echo *)"])}, c)
            self.assertIn("DECISION: deny", out, c)

    def test_env_assignment(self):
        _, out, _ = run({"user": perms(deny=["Bash(rm *)"])}, "FOO=1 rm x")
        self.assertIn("DECISION: deny", out)
        _, out, _ = run({"user": perms(allow=["Bash(make *)"])}, "FOO=1 make test")
        self.assertIn("DECISION: no-rule", out)

    def test_wrappers(self):
        _, out, _ = run({"user": perms(deny=["Bash(npm test *)"])}, "timeout 30 npm test")
        self.assertIn("DECISION: deny", out)
        _, out, _ = run({"user": perms(allow=["Bash(timeout *)"])}, "timeout 30 rm x")
        self.assertIn("DECISION: no-rule", out)

    def test_exec_wrappers_need_an_exact_rule(self):
        _, out, _ = run({"user": perms(allow=["Bash(find *)"])}, "find . -delete")
        self.assertIn("DECISION: no-rule", out)
        _, out, _ = run({"user": perms(allow=["Bash(find . -delete)"])}, "find . -delete")
        self.assertIn("DECISION: allow", out)
        _, out, _ = run({"user": perms(allow=["Bash(find *)"])}, "find . -name x")
        self.assertIn("DECISION: allow", out)

    def test_guarded_strings_from_command_or_rule(self):
        _, out, _ = run({"user": perms(deny=["Bash"])}, "ssh host")
        self.assertIn("DECISION: deny", out)
        self.assertNotIn("Bash(ssh", out)
        for c in ("SSH host", "grep 'Bash(ssh' f"):
            _, out, _ = run({"user": perms(deny=["Bash"])}, c)
            self.assertNotIn("bash(ssh", out.lower(), c)
        _, out, _ = run({"user": perms(deny=["Bash(ssh *)"])}, "ssh host")
        self.assertIn("Bash(ssh", out)
        _, out, _ = run({"user": perms(deny=["Bash(echo disableBypassPermissionsMode*)"])},
                        "echo disableBypassPermissionsMode")
        self.assertIn("DECISION: deny", out)
        self.assertNotIn("disablebypasspermissionsmode", out.lower())

    def test_quote_forms_and_comments_never_hide_a_deny(self):
        layers = {"user": perms(allow=["Bash(echo *)"], deny=["Bash(rm *)"])}
        for c in ("echo $'\\'' ; rm -rf x #'", "echo hi # it's\nrm -rf x # '"):
            _, out, _ = run(layers, c)
            self.assertIn("DECISION: deny", out, c)
        _, out, _ = run(layers, "cat <<EOF\nhi\nEOF")
        self.assertNotIn("DECISION: allow", out)
        _, out, _ = run({"user": perms(allow=["Bash(cat *)"])}, "cat <<EOF")
        self.assertNotIn("DECISION: allow", out)

    def test_fd_redirect_is_not_a_separator(self):
        _, out, _ = run({"user": perms(allow=["Bash(npm test *)"])}, "npm test 2>&1")
        self.assertIn("SUBCOMMANDS: 1", out)
        self.assertIn("DECISION: allow", out)

    def test_wrapper_allow_is_not_computed_and_says_so(self):
        _, out, _ = run({"user": perms(allow=["Bash(npm test *)"])}, "timeout 30 npm test")
        self.assertIn("DECISION: no-rule", out)
        self.assertIn("this checker does not compute allow past wrappers or env assignments and prints "
                      "no-rule there, which is not a statement about what Claude Code does", out)

    def test_non_list_rules_are_bad_input(self):
        p = subprocess.run([sys.executable, SCRIPT, "--inline", 'user={"permissions":{"deny":"Bash"}}',
                            "--command", "x"], capture_output=True, text=True)
        self.assertEqual((p.returncode, p.stdout), (2, ""))


if __name__ == "__main__":
    unittest.main()
