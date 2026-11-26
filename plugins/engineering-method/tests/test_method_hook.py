"""Tests for the engineering-method hooks (scripts/method_hook.py, hooks/hooks.json).

The script is run as a subprocess, the way the harness runs it: JSON on stdin,
hook JSON (or nothing) on stdout, always exit 0. State goes to a temp
CLAUDE_PLUGIN_DATA so tests never touch real session memory.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
SCRIPT = os.path.join(PLUGIN, "scripts", "method_hook.py")
HOOKS_JSON = os.path.join(PLUGIN, "hooks", "hooks.json")
REFS = os.path.join(PLUGIN, "skills", "engineering-method", "references")


def run(mode, payload, data_dir, raw_stdin=None):
    env = dict(os.environ)
    if data_dir is None:
        env.pop("CLAUDE_PLUGIN_DATA", None)
    else:
        env["CLAUDE_PLUGIN_DATA"] = data_dir
    stdin = raw_stdin if raw_stdin is not None else json.dumps(payload)
    return subprocess.run([sys.executable, SCRIPT, mode], input=stdin, env=env,
                          capture_output=True, text=True)


def context(proc):
    """The additionalContext string, or None when the hook was silent."""
    if not proc.stdout.strip():
        return None
    return json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="methodhook-")
        self.addCleanup(self._tmp.cleanup)
        self.data = self._tmp.name

    def prompt(self, text, session="s1"):
        return run("--prompt", {"prompt": text, "session_id": session}, self.data)

    def start(self, source="startup", session="s1"):
        return run("--session-start", {"source": source, "session_id": session}, self.data)


class SessionStart(Base):
    def test_valid_hook_json_for_each_source(self):
        for source in ("startup", "clear", "compact", "resume"):
            p = self.start(source)
            self.assertEqual(p.returncode, 0)
            out = json.loads(p.stdout)
            hso = out["hookSpecificOutput"]
            self.assertEqual(hso["hookEventName"], "SessionStart")
            self.assertTrue(hso["additionalContext"])
            self.assertIn("engineering-method", hso["additionalContext"])

    def test_compact_line_only_for_compact(self):
        self.assertIn("context was just compacted", context(self.start("compact")))
        for source in ("startup", "clear", "resume"):
            self.assertNotIn("compacted", context(self.start(source)))

    def test_brief_names_tiers_and_loading_rule(self):
        text = context(self.start("startup"))
        for needle in ("exploration", "internal", "live", "plan", "deploy", "references"):
            self.assertIn(needle, text)

    def test_brief_tier_rule_matches_owner_update_exception(self):
        """SKILL.md §1 lets an owner update open with "Needs you"; the brief must not contradict it."""
        text = context(self.start("startup"))
        self.assertIn("owner update", text)

    def test_brief_within_limit(self):
        for source in ("startup", "clear", "compact"):
            self.assertLessEqual(len(context(self.start(source))), 1500)

    def test_session_start_resets_stage_memory(self):
        self.assertIsNotNone(context(self.prompt("please review this")))
        self.assertIsNone(context(self.prompt("review again")))
        self.start("clear")
        self.assertIsNotNone(context(self.prompt("review once more")))

    def test_broken_stdin_still_emits_fallback(self):
        p = run("--session-start", None, self.data, raw_stdin="not json{")
        self.assertEqual(p.returncode, 0)
        self.assertNotIn("Traceback", p.stderr + p.stdout)
        self.assertIn("engineering-method", context(p))


class Prompt(Base):
    def test_no_stage_words_is_silent(self):
        p = self.prompt("what time is it in Tokyo")
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout, "")

    def test_announces_once_then_silent(self):
        first = context(self.prompt("let's review the change"))
        self.assertIn("stage review", first)
        self.assertIn("superpowers:requesting-code-review", first)
        self.assertIn("review-loop.md", first)
        self.assertIsNone(context(self.prompt("review it again")))

    def test_hook_event_name(self):
        out = json.loads(self.prompt("deploy it").stdout)
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")

    def test_new_stage_speaks(self):
        self.prompt("plan the work")
        text = context(self.prompt("now implement it"))
        self.assertIn("stage build", text)

    def test_stage_without_skill_omits_skill(self):
        text = context(self.prompt("rollback the change"))
        self.assertIn("stage deploy", text)
        self.assertNotIn("superpowers", text)
        self.assertIn("live-system-changes.md", text)

    def test_new_session_speaks_again(self):
        self.assertIsNotNone(context(self.prompt("review this", session="a")))
        self.assertIsNone(context(self.prompt("review this", session="a")))
        self.assertIsNotNone(context(self.prompt("review this", session="b")))

    def test_earliest_stage_word_wins(self):
        self.assertIn("stage plan", context(self.prompt("plan it, then deploy it")))

    def test_inflections(self):
        cases = {"planning": "plan", "we built it": "build", "reviewing": "review",
                 "deployed": "deploy", "merged": "merge", "releasing": "release",
                 "shipped": "release", "tests": "test"}
        for i, (text, stage) in enumerate(cases.items()):
            self.assertIn("stage %s" % stage, context(self.prompt(text, session="i%d" % i)), text)

    def test_slash_command_name_ignored(self):
        # command name "plan-layer" must not count as plan; "status" is a report word
        text = context(self.prompt("/plan-layer status"))
        self.assertIn("stage report", text)
        self.assertIsNone(context(self.prompt("/review", session="x")))
        self.assertIn("stage build", context(self.prompt("/plan fix the heading", session="y")))

    def test_whole_word_only(self):
        for i, text in enumerate(("the planet is big", "contest", "prereview", "update it and check it")):
            self.assertEqual(self.prompt(text, session="w%d" % i).stdout, "", text)

    def test_case_insensitive(self):
        self.assertIn("stage review", context(self.prompt("REVIEW this")))

    def test_message_points_at_skill_row(self):
        text = context(self.prompt("review this", session="row"))
        self.assertEqual(text, "engineering-method: stage review \u2014 re-read SKILL.md \u00a73 row "
                               "'review', load superpowers:requesting-code-review, read "
                               "references/review-loop.md before acting; keep the stakes tier you named.")

    def test_message_without_skill_points_at_row(self):
        text = context(self.prompt("rollback the change", session="row2"))
        self.assertIn("re-read SKILL.md \u00a73 row 'deploy', read references/live-system-changes.md", text)
        self.assertNotIn("load ", text)

    def test_message_within_limit(self):
        for i, w in enumerate(("plan", "build", "review", "test", "deploy", "merge", "release", "report", "debug")):
            text = context(self.prompt(w, session="m%d" % i))
            self.assertLessEqual(len(text), 400)

    def test_broken_stdin_silent(self):
        for raw in ("", "not json{", "[]", '{"prompt": 5}', "null"):
            p = run("--prompt", None, self.data, raw_stdin=raw)
            self.assertEqual((p.returncode, p.stdout), (0, ""), raw)
            self.assertNotIn("Traceback", p.stderr)

    def test_missing_data_dir_never_crashes(self):
        for data in (None, os.path.join(self.data, "does", "not", "exist")):
            p = run("--prompt", {"prompt": "review", "session_id": "q"}, data)
            self.assertEqual(p.returncode, 0)
            self.assertNotIn("Traceback", p.stderr)
            self.assertLess(len(p.stdout), 10000)

    def test_corrupt_state_file_never_crashes(self):
        with open(os.path.join(self.data, "method-stage.json"), "w") as fh:
            fh.write("{broken")
        p = self.prompt("review")
        self.assertEqual(p.returncode, 0)
        self.assertIn("stage review", context(p))

    def test_old_entries_pruned(self):
        path = os.path.join(self.data, "method-stage.json")
        with open(path, "w") as fh:
            json.dump({"old": {"stage": "plan", "at": 1}}, fh)
        self.prompt("review")
        with open(path) as fh:
            state = json.load(fh)
        self.assertNotIn("old", state)
        self.assertIn("s1", state)


class FixRound(Base):
    """Review round: set memory, false positives, false negatives, brief format."""
    n = 0

    def stage_of(self, text):
        FixRound.n += 1
        c = context(self.prompt(text, session="fx%d" % FixRound.n))
        if c is None:
            return None
        return re.search(r"stage (\w+)", c).group(1)

    def test_alternating_stages_each_speak_once(self):
        spoken = [context(self.prompt(t)) is not None for t in
                  ("fix it", "run the tests", "fix that one too", "tests again", "fix", "tests")]
        self.assertEqual(spoken, [True, True, False, False, False, False])

    def test_session_start_resets_set(self):
        self.prompt("fix it")
        self.prompt("run the tests")
        self.start("compact")
        self.assertIsNotNone(context(self.prompt("fix it")))

    def test_skips_code_fences(self):
        self.assertIsNone(self.stage_of("what is this?\n```\ndeploy now\n```"))
        self.assertEqual(self.stage_of("```\nmerge\n```\nplease review"), "review")

    def test_skips_tag_wrapped_blocks(self):
        self.assertIsNone(self.stage_of("<pasted_content id=1>deploy and release</pasted_content>"))
        self.assertIsNone(self.stage_of("hello <system-reminder>rollback happened</system-reminder> ok"))
        self.assertEqual(self.stage_of("<pasted_content>release</pasted_content> then review"), "review")
        # other tags: the token goes, the contents stay
        self.assertEqual(self.stage_of("<foo>release</foo> then review"), "release")

    def test_skips_log_and_code_lines(self):
        for line in ("2026-11-16 10:00:01 deploy failed", "10:00:01 deploy failed",
                     "ERROR deploy failed", "WARN restart needed", "INFO release",
                     "Traceback (most recent call last): deploy", ">>> deploy()",
                     "$ git push", "def deploy():", "    deploy()", "\tdeploy()"):
            self.assertIsNone(self.stage_of("what does this mean\n" + line), line)

    def test_git_status_ignored_but_not_git_push_merge(self):
        self.assertIsNone(self.stage_of("run git status"))
        self.assertEqual(self.stage_of("git status then review"), "review")
        self.assertEqual(self.stage_of("git merge it"), "merge")
        self.assertEqual(self.stage_of("git push it"), "merge")
        self.assertEqual(self.stage_of("what is the status"), "report")

    def test_command_name_wrapper_stripped(self):
        self.assertEqual(self.stage_of("<command-name>/plan-layer</command-name> status"), "report")
        self.assertIsNone(self.stage_of("<command-name>/review</command-name>"))

    def test_new_words(self):
        cases = {"prod": "deploy", "production": "deploy", "is it live": "deploy",
                 "go-live": "deploy", "roll back": "deploy", "rolling back": "deploy",
                 "rolled back": "deploy", "re-deploy": "deploy", "unit-tests": "test",
                 "test-suite": "test", "pr": "merge", "open a pull request": "merge",
                 "commit": "merge", "pytest": "test", "debug": "debug"}
        for text, stage in cases.items():
            self.assertEqual(self.stage_of(text), stage, text)

    def test_still_whole_word(self):
        for text in ("planet", "contest", "livestock", "prayer", "debugger"):
            self.assertIsNone(self.stage_of(text), text)

    def test_brief_reference_paths(self):
        text = context(self.start("startup"))
        self.assertIn("deploy -> references/live-system-changes.md", text)
        self.assertIn("review -> superpowers:requesting-code-review -> references/review-loop.md", text)
        self.assertNotIn("-> - ->", text)


class Robustness(Base):
    """Round 2: bounded, linear-time scanning; list lines are not code."""

    def timed(self, text):
        import time
        t = time.time()
        p = self.prompt(text)
        return p, time.time() - t

    def test_megabyte_of_unclosed_tags_is_fast(self):
        for chunk in ("<a> ", "<li>x\n"):
            p, secs = self.timed(chunk * (1024 * 1024 // len(chunk)) + " deploy")
            self.assertEqual(p.returncode, 0)
            self.assertLess(secs, 1.0, repr(chunk))

    def test_many_unclosed_tags_then_stage_word_near_start(self):
        p, secs = self.timed("deploy it\n" + "<li>item text here\n" * 50000)
        self.assertLess(secs, 1.0)
        self.assertIn("stage deploy", context(p))

    def test_stage_word_after_4096_chars_ignored(self):
        self.assertEqual(self.prompt("x " * 2100 + "deploy").stdout, "")
        self.assertIn("stage deploy", context(self.prompt("x " * 100 + "deploy", session="n")))

    def test_deployment_words(self):
        for i, w in enumerate(("deployment", "deployments")):
            self.assertIn("stage deploy", context(self.prompt(w, session="d%d" % i)))

    def test_indented_list_lines_are_not_code(self):
        for i, line in enumerate(("    - deploy it", "    * deploy it", "    1. deploy it")):
            self.assertIn("stage deploy", context(self.prompt("steps:\n" + line, session="l%d" % i)), line)
        self.assertEqual(self.prompt("steps:\n    deploy()", session="c").stdout, "")


class LongPaste(Base):
    """Round 3: wrappers are stripped over the whole prompt, then the cap applies."""

    def paste(self, tail):
        return "<pasted_content id=1>" + "deploy the thing, release notes. " * 200 + "</pasted_content> " + tail

    def test_long_paste_stage_words_ignored(self):
        text = self.paste("summarise this")
        self.assertGreater(text.index("</pasted_content>"), 6000)
        self.assertEqual(self.prompt(text).stdout, "")

    def test_request_after_long_paste_is_seen(self):
        self.assertIn("stage review", context(self.prompt(self.paste("review this"))))

    def test_unclosed_wrapper_drops_the_rest(self):
        import time
        text = "<pasted_content>" + "deploy and release now. " * 45000
        self.assertGreater(len(text), 1000000)
        t = time.time()
        p = self.prompt(text)
        self.assertLess(time.time() - t, 1.0)
        self.assertEqual(p.stdout, "")

    def test_megabyte_of_unclosed_generic_tags_still_fast(self):
        import time
        for chunk in ("<a> ", "<li>x\n"):
            t = time.time()
            p = self.prompt("review it " + chunk * (1024 * 1024 // len(chunk)), session=repr(chunk))
            self.assertLess(time.time() - t, 1.0, repr(chunk))
            self.assertIn("stage review", context(p))

    def test_long_fence_stage_words_ignored(self):
        text = "```\n" + "deploy it\n" * 800 + "```\nsummarise this"
        self.assertEqual(self.prompt(text).stdout, "")


class TagTokens(Base):
    """Round 4: only known wrappers are block-stripped; other tags lose just the token."""

    def test_thousands_of_distinct_unclosed_tags_fast(self):
        import time
        text = "review this " + " ".join("<t%d>" % i for i in range(30000))
        self.assertGreater(len(text), 200000)
        t = time.time()
        p = self.prompt(text)
        self.assertLess(time.time() - t, 1.0)
        self.assertIn("stage review", context(p))

    def test_generic_type_syntax_does_not_hide_the_request(self):
        self.assertIn("stage build", context(self.prompt("why does Vec<T> fail here, fix it")))

    def test_stray_closing_tag_removed_contents_kept(self):
        self.assertIn("stage review", context(self.prompt("</div> review it")))


class DebugStage(Base):
    """0.4.0: a debugging prompt routes to systematic-debugging and the investigation reference."""
    n = 0

    def stage_of(self, text):
        DebugStage.n += 1
        c = context(self.prompt(text, session="dbg%d" % DebugStage.n))
        return None if c is None else re.search(r"stage (\w+)", c).group(1)

    def test_debug_words_and_phrase(self):
        for text in ("debug the agent", "debugging this", "investigate the refusal",
                     "diagnose it", "there is a bug in the parser",
                     "what was the root cause"):
            self.assertEqual(self.stage_of(text), "debug", text)

    def test_debug_message_names_skill_and_reference(self):
        text = context(self.prompt("investigate this", session="dm"))
        self.assertIn("load superpowers:systematic-debugging", text)
        self.assertIn("references/root-cause-investigation.md", text)
        self.assertLessEqual(len(text), 400)

    def test_debug_message_puts_evidence_before_any_cause(self):
        text = context(self.prompt("investigate this", session="dm2"))
        self.assertIn("no cause, suspect list or fix until RC-1 to RC-4", text)
        self.assertIn("(tier b, c)", text)
        self.assertIn("are done, requested or skipped", text)
        self.assertLessEqual(len(text), 400)
        other = context(self.prompt("review this", session="dm3"))
        self.assertNotIn("RC-1", other)

    def test_a_debug_word_outranks_an_earlier_fix_word(self):
        for text in ("fix the bug in the parser", "fix the bug in login",
                     "fix it, then investigate why it broke"):
            self.assertEqual(self.stage_of(text), "debug", text)

    def test_other_build_words_keep_build(self):
        for text in ("implement a debug flag", "build with debug symbols",
                     "refactor the debug logging", "build a bug tracker",
                     "build the investigation dashboard"):
            self.assertEqual(self.stage_of(text), "build", text)

    def test_fix_without_a_debug_word_stays_build(self):
        for text in ("fix it", "fix the typo in the heading", "implement the fix"):
            self.assertEqual(self.stage_of(text), "build", text)

    def test_an_earlier_non_build_stage_still_wins(self):
        self.assertEqual(self.stage_of("plan the fix for the bug"), "plan")
        self.assertEqual(self.stage_of("review the bug fix"), "review")

    def test_a_nearer_non_build_stage_blocks_the_debug_override(self):
        self.assertEqual(self.stage_of("fix the typo, then deploy to production; "
                                       "the bug report can wait"), "deploy")
        self.assertEqual(self.stage_of("fix it then merge, the bug is known"), "merge")

    def test_inflected_fix_and_bug_words_route_to_debug(self):
        for text in ("fixed the bug", "fixing bugs in the parser", "fixes the bugs here",
                     "fixed it, bugs remain"):
            self.assertEqual(self.stage_of(text), "debug", text)

    def test_why_questions_do_not_claim_the_debug_stage(self):
        self.assertIsNone(context(self.prompt("why did we decide on Postgres?", session="why")))
        text = context(self.prompt("debug the login failure", session="why"))
        self.assertIn("stage debug", text)

    def test_debug_words_are_whole_words(self):
        for text in ("debugger", "bugle", "investigator", "humbug"):
            self.assertIsNone(self.stage_of(text), text)

    def test_brief_lists_the_debug_stage(self):
        text = context(self.start("startup"))
        self.assertIn("debug -> superpowers:systematic-debugging -> "
                      "references/root-cause-investigation.md", text)
        for source in ("startup", "clear", "compact"):
            self.assertLessEqual(len(context(self.start(source))), 1500)


class Wiring(unittest.TestCase):
    def setUp(self):
        with open(HOOKS_JSON) as fh:
            self.hooks = json.load(fh)["hooks"]

    def test_session_start_entry(self):
        entry = self.hooks["SessionStart"][0]
        self.assertEqual(entry["matcher"], "startup|clear|compact")
        cmd = entry["hooks"][0]["command"]
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", cmd)
        self.assertIn("--session-start", cmd)
        self.assertTrue(cmd.endswith("2>/dev/null || true"))

    def test_prompt_entry(self):
        entry = self.hooks["UserPromptSubmit"][0]
        self.assertNotIn("matcher", entry)
        cmd = entry["hooks"][0]["command"]
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", cmd)
        self.assertIn("--prompt", cmd)
        for h in (self.hooks["SessionStart"][0]["hooks"][0], entry["hooks"][0]):
            self.assertLessEqual(h["timeout"], 10)
            self.assertEqual(h["shell"], "bash")
            self.assertTrue(h["statusMessage"])

    def test_every_stage_reference_exists(self):
        sys.path.insert(0, os.path.join(PLUGIN, "scripts"))
        import method_hook
        missing = [r for s in method_hook.STAGES for r in s["references"]
                   if not os.path.isfile(os.path.join(REFS, r))]
        self.assertEqual(missing, [])


def load_hook():
    """Import scripts/method_hook.py by path (as test_skill_budget.load_hook does)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("method_hook", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestStageNote(unittest.TestCase):
    def test_test_stage_names_conformance_within_400(self):
        hook = load_hook()
        st = [s for s in hook.STAGES if s["stage"] == "test"][0]
        msg = hook.stage_message(st)
        self.assertIn("plan_conformance.py", msg)
        self.assertLessEqual(len(msg), 400)
        self.assertTrue(msg.endswith("named."), "the message was truncated at 400 characters")


if __name__ == "__main__":
    unittest.main()
