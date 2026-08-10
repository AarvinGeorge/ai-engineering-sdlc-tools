#!/usr/bin/env python3
"""Tests for plan-layer. Standard library only, like the thing they test.

  python3 tests/test_plan_layer.py

These cover the behaviours that would embarrass the tool in someone else's
repository: talking when uninvited, crashing on a broken plan, passing a check
that tested nothing, and losing a project's own contract keys.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
SCRIPTS = os.path.join(PLUGIN, "scripts")
sys.path.insert(0, SCRIPTS)


def run(script, *args, cwd=None, project=None, stdin="{}"):
    env = dict(os.environ)
    if project:
        env["CLAUDE_PROJECT_DIR"] = project
    else:
        env.pop("CLAUDE_PROJECT_DIR", None)
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args],
                          cwd=cwd or project or HERE, env=env, input=stdin,
                          capture_output=True, text=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="planlayer-")
        subprocess.run(["git", "init", "-q"], cwd=self.dir, capture_output=True)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def page(self):
        with open(os.path.join(self.dir, "plan", "index.html")) as fh:
            return fh.read()

    def write(self, d):
        with open(os.path.join(self.dir, "plan", "plan.json"), "w") as fh:
            json.dump(d, fh, indent=2)

    def make_plan(self, **over):
        os.makedirs(os.path.join(self.dir, "plan"), exist_ok=True)
        with open(os.path.join(PLUGIN, "templates", "plan.json")) as fh:
            d = json.load(fh)
        d["meta"]["updated"] = "2026-01-01T00:00:00Z"
        d["meta"]["changelog"][0]["date"] = "2026-01-01"
        d.update(over)
        self.write(d)
        return d


class TestUninvited(Base):
    """A project that never opted in must not hear from us."""

    def test_brief_is_completely_silent(self):
        r = run("brief.py", "--session-start", project=self.dir)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "", "brief.py spoke in a project with no plan")

    def test_render_and_check_exit_zero(self):
        for s in ("render.py", "check.py"):
            r = run(s, project=self.dir)
            self.assertEqual(r.returncode, 0, "%s failed where no plan exists" % s)

    def test_no_page_is_created(self):
        run("render.py", project=self.dir)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "plan", "index.html")))


class TestRender(Base):
    def test_template_renders(self):
        self.make_plan()
        r = run("render.py", project=self.dir)
        self.assertEqual(r.returncode, 0, r.stderr)
        page = self.page()
        self.assertIn("data-fingerprint=", page)
        self.assertIn("PROJECT NAME", page)

    def test_page_is_self_contained(self):
        """No external requests. This is what makes the page shareable."""
        self.make_plan()
        run("render.py", project=self.dir)
        page = self.page()
        for forbidden in ("<script", "http://", "https://", "<link", "@import", "<img"):
            self.assertNotIn(forbidden, page, "page reaches outside itself: %s" % forbidden)

    def test_empty_sections_are_omitted_not_broken(self):
        self.make_plan(capabilities=[], parked=[], invariants=[], glossary=[], systems=[])
        r = run("render.py", project=self.dir)
        self.assertEqual(r.returncode, 0)
        page = self.page()
        self.assertNotIn("<table", page)
        self.assertIn("Next", page)

    def test_arbitrary_contract_keys_survive(self):
        """An allow-list of key names silently drops a project's own wording."""
        self.make_plan(contract={"for_agent": "A", "for_priya": "B"})
        run("render.py", project=self.dir)
        page = self.page()
        self.assertIn("For Priya", page)
        self.assertIn(">B<", page)

    def test_stale_detection(self):
        self.make_plan()
        run("render.py", project=self.dir)
        self.assertEqual(run("render.py", "--check", project=self.dir).returncode, 0)
        with open(os.path.join(self.dir, "plan", "plan.json")) as fh:
            d = json.load(fh)
        d["meta"]["subtitle"] = "changed underneath the page"
        self.write(d)
        self.assertEqual(run("render.py", "--check", project=self.dir).returncode, 1,
                         "a page rendered from different data reported itself in sync")


class TestFigures(Base):
    def test_project_figures_are_used(self):
        self.make_plan()
        with open(os.path.join(self.dir, "plan", "figures.py"), "w") as fh:
            fh.write("def build(data):\n    return '<figure id=\"mine\"></figure>'\n")
        run("render.py", project=self.dir)
        self.assertIn('id="mine"', self.page())

    def test_figure_css_reaches_the_stylesheet(self):
        """Markup without styles is worse than no figure.

        An SVG rect with no fill rule renders solid black with invisible text,
        so the page looks broken rather than plain. This shipped once.
        """
        self.make_plan()
        with open(os.path.join(self.dir, "plan", "figures.py"), "w") as fh:
            fh.write('CSS = "\\n  .dg-box{fill:none;stroke:red}\\n"\n'
                     'def build(data):\n'
                     '    return \'<figure><svg><rect class="dg-box"/></svg></figure>\'\n')
        run("render.py", project=self.dir)
        page = self.page()
        self.assertIn(".dg-box{fill:none;stroke:red}", page,
                      "figure CSS never reached the stylesheet")
        self.assertLess(page.index(".dg-box{"), page.index("</style>"),
                        "figure CSS landed outside the stylesheet")

    ORPHAN_FIGURES = (
        'CSS = "\\n  .known{fill:none}\\n"\n'
        'def build(data):\n'
        '    return (\'<figure><svg><rect class="known"/>\'\n'
        '            \'<rect class="orphan"/></svg></figure>\')\n'
    )

    def test_every_class_used_by_figures_has_a_rule(self):
        """The generic guard against the bug above: markup that references a
        class the stylesheet never defines is a silently broken figure."""
        import re as _re
        self.make_plan()
        with open(os.path.join(self.dir, "plan", "figures.py"), "w") as fh:
            fh.write(self.ORPHAN_FIGURES)
        r = run("render.py", project=self.dir)
        self.assertNotIn("failed to load", r.stdout, "the fixture is not valid Python")
        page = self.page()
        style = page[page.index("<style>"):page.index("</style>")]
        used = set()
        for m in _re.finditer(r'class="([^"]+)"', page[page.index("</style>"):]):
            used.update(m.group(1).split())
        defined = set(_re.findall(r"\.([A-Za-z][\w-]*)", style))
        self.assertIn("known", defined, "figure CSS did not reach the stylesheet")
        self.assertIn("orphan", used - defined,
                      "the orphan-class detector itself is broken")

    def test_broken_figures_do_not_cost_the_page(self):
        self.make_plan()
        with open(os.path.join(self.dir, "plan", "figures.py"), "w") as fh:
            fh.write("def build(data):\n    raise RuntimeError('boom')\n")
        r = run("render.py", project=self.dir)
        self.assertEqual(r.returncode, 0, "a broken figure took the whole page down")
        self.assertTrue(os.path.exists(os.path.join(self.dir, "plan", "index.html")))


class TestGate(Base):
    def test_clean_plan_passes(self):
        self.make_plan()
        run("render.py", project=self.dir)
        self.assertEqual(run("check.py", project=self.dir).returncode, 0)

    def test_progress_without_evidence_fails(self):
        d = self.make_plan()
        d["capabilities"][0].update(build="done", evidence="")
        self.write(d)
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("no evidence", r.stdout)

    def test_unknown_stage_fails(self):
        d = self.make_plan()
        d["plans"]["next"][0]["stage"] = "wishful-thinking"
        self.write(d)
        run("render.py", project=self.dir)
        self.assertEqual(run("check.py", project=self.dir).returncode, 1)

    def test_building_without_a_plan_document_fails(self):
        d = self.make_plan()
        d["plans"]["now"] = [{"name": "X", "status": "going", "updated": "2026-01-01",
                              "stage": "building", "plan_file": None}]
        self.write(d)
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("without a written plan", r.stdout)

    def test_dangling_capability_reference_fails(self):
        d = self.make_plan()
        d["plans"]["next"][0]["capability"] = 99
        self.write(d)
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("does not exist", r.stdout)

    def test_unlinked_plan_item_drifts(self):
        """A plan list and a capabilities table that never reference each other
        are two documents sharing a page."""
        self.make_plan()          # template items carry no capability
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertIn("names no capability", r.stdout)
        self.assertEqual(r.returncode, 0, "an unlinked item is drift, not a hard failure")

    def test_valid_capability_reference_is_clean(self):
        d = self.make_plan()
        d["plans"]["next"][0]["capability"] = d["capabilities"][0]["id"]
        self.write(d)
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertNotIn("names no capability", r.stdout)
        page = self.page()
        self.assertIn("capref", page, "the link is gated but never shown to the reader")

    def test_stale_page_fails(self):
        self.make_plan()
        r = run("check.py", project=self.dir)  # never rendered
        self.assertEqual(r.returncode, 1)

    def test_version_changelog_mismatch_fails(self):
        d = self.make_plan()
        d["meta"]["plan_version"] = "9.9.9"
        self.write(d)
        run("render.py", project=self.dir)
        self.assertEqual(run("check.py", project=self.dir).returncode, 1)

    def test_commit_drift_message_is_in_one_timezone(self):
        """A true finding printed across two zones reads as nonsense.

        git reports commit times with a local offset; meta.updated is usually Z.
        Both must be shown in UTC or the message looks self-contradictory.
        """
        d = self.make_plan()
        d["meta"]["updated"] = "2000-01-01T00:00:00Z"      # guarantee the drift fires
        self.write(d)
        run("render.py", project=self.dir)
        # The signal is about work landing OUTSIDE the plan directory -- a commit
        # touching only plan/ is the plan being updated, which is the opposite of
        # drift. The first version of this test committed only plan files and
        # correctly got nothing.
        with open(os.path.join(self.dir, "src.py"), "w") as fh:
            fh.write("# substantive work\n")
        subprocess.run(["git", "add", "-A"], cwd=self.dir, capture_output=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                        "commit", "-qm", "work"], cwd=self.dir, capture_output=True)
        out = run("check.py", project=self.dir).stdout
        line = next((l for l in out.splitlines() if "newer than meta.updated" in l), "")
        self.assertTrue(line, "commit-drift signal did not fire: %s" % out)
        self.assertEqual(line.count("Z"), 2,
                         "both timestamps must be rendered in UTC: %s" % line)

    def test_porcelain_paths_are_parsed_intact(self):
        """A bare .strip() eats porcelain's leading status column on line one,
        shifting every path by a character. That bug shipped once; it stays tested."""
        import plan_lib as L
        self.make_plan()
        with open(os.path.join(self.dir, "zzz.txt"), "w") as fh:
            fh.write("x")
        out = L.git(self.dir, "status", "--porcelain")
        paths = [ln[3:] for ln in out.splitlines()]
        self.assertIn("zzz.txt", paths, "porcelain parse lost or shifted a path: %r" % paths)


class TestBrief(Base):
    def test_emits_valid_hook_json(self):
        self.make_plan()
        run("render.py", project=self.dir)
        r = run("brief.py", "--session-start", project=self.dir)
        d = json.loads(r.stdout)
        self.assertEqual(d["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertIn("PLAN STATE", d["hookSpecificOutput"]["additionalContext"])

    def test_pre_compact_mode(self):
        self.make_plan()
        r = run("brief.py", "--pre-compact", project=self.dir)
        d = json.loads(r.stdout)
        self.assertEqual(d["hookSpecificOutput"]["hookEventName"], "PreCompact")

    def test_corrupt_plan_still_exits_zero(self):
        """A broken plan must never block a session."""
        os.makedirs(os.path.join(self.dir, "plan"), exist_ok=True)
        with open(os.path.join(self.dir, "plan", "plan.json"), "w") as fh:
            fh.write("{ not json")
        r = run("brief.py", "--session-start", project=self.dir)
        self.assertEqual(r.returncode, 0)
        json.loads(r.stdout)  # must still be a well-formed hook response


class TestAssertions(Base):
    """The plan checking itself against the real system."""

    def test_matching_assertion_passes(self):
        d = self.make_plan()
        d["assertions"] = [{"claim": "echo works", "run": "echo hello", "expect": "hello"}]
        d["meta"]["assertions_verified"] = "2026-01-01T00:00:00Z"
        self.write(d)
        run("render.py", project=self.dir)
        r = run("check.py", "--verify", project=self.dir)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("MATCH", r.stdout)

    def test_mismatching_assertion_fails(self):
        d = self.make_plan()
        d["assertions"] = [{"claim": "pid unchanged", "run": "echo 999", "expect": "3001002"}]
        self.write(d)
        run("render.py", project=self.dir)
        r = run("check.py", "--verify", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("MISMATCH", r.stdout)

    def test_regex_match_mode(self):
        d = self.make_plan()
        d["assertions"] = [{"claim": "healthy", "run": "echo 'Up 5 days (healthy)'",
                            "expect": "healthy", "match": "regex"}]
        self.write(d)
        run("render.py", project=self.dir)
        self.assertEqual(run("check.py", "--verify", project=self.dir).returncode, 0)

    def test_assertions_never_run_from_the_hook(self):
        """A repository must not be able to execute its author's commands just
        by being opened. Assertions are explicit-only, forever."""
        d = self.make_plan()
        sentinel = os.path.join(self.dir, "SHOULD_NOT_EXIST")
        d["assertions"] = [{"claim": "malicious", "run": "touch %s" % sentinel, "expect": ""}]
        self.write(d)
        run("render.py", project=self.dir)
        run("brief.py", "--session-start", project=self.dir)
        run("brief.py", "--pre-compact", project=self.dir)
        run("check.py", project=self.dir)          # the ordinary gate, no --verify
        self.assertFalse(os.path.exists(sentinel),
                         "an assertion executed without --verify")

    def test_declared_but_never_verified_drifts(self):
        d = self.make_plan()
        d["assertions"] = [{"claim": "x", "run": "true", "expect": ""}]
        self.write(d)
        run("render.py", project=self.dir)
        self.assertIn("never recorded as run", run("check.py", project=self.dir).stdout)


class TestEdgeCases(Base):
    def test_duplicate_capability_ids_fail(self):
        d = self.make_plan()
        d["capabilities"].append(dict(d["capabilities"][0]))
        self.write(d)
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("duplicate capability ids", r.stdout)

    def test_shared_plan_file_fails(self):
        d = self.make_plan()
        d["plans"]["next"] = [
            {"name": "A", "why": "w", "unblocks": "u", "stage": "intent", "plan_file": "p.md"},
            {"name": "B", "why": "w", "unblocks": "u", "stage": "intent", "plan_file": "p.md"}]
        self.write(d)
        run("render.py", project=self.dir)
        self.assertEqual(run("check.py", project=self.dir).returncode, 1)

    def test_alarm_without_detail_fails(self):
        d = self.make_plan()
        d["invariants"] = [{"rule": "backups exist", "state": "broken", "detail": ""}]
        self.write(d)
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("alarm nobody can act on", r.stdout)

    def test_parked_without_trigger_fails(self):
        d = self.make_plan()
        d["parked"] = [{"id": "P1", "q": "which model?", "trigger": ""}]
        self.write(d)
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("parked without one is dropped", r.stdout)

    def test_future_timestamp_fails(self):
        d = self.make_plan()
        d["meta"]["updated"] = "2099-01-01T00:00:00Z"
        self.write(d)
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("future", r.stdout)

    def test_unparseable_timestamp_fails(self):
        d = self.make_plan()
        d["meta"]["updated"] = "last tuesday"
        self.write(d)
        run("render.py", project=self.dir)
        self.assertEqual(run("check.py", project=self.dir).returncode, 1)

    def test_recorded_item_still_active_drifts(self):
        d = self.make_plan()
        d["plans"]["now"] = [{"name": "X", "status": "done", "updated": "2026-01-01",
                              "stage": "recorded", "plan_file": "p.md"}]
        self.write(d)
        run("render.py", project=self.dir)
        self.assertIn("belongs in plans.done", run("check.py", project=self.dir).stdout)


class TestContrast(unittest.TestCase):
    """Every palette token must clear WCAG AA against both grounds it sits on.

    Two tokens shipped at 4.31:1 and 4.09:1 — close enough to look fine and
    still fail. Colour is the one thing that cannot be eyeballed, so it is
    measured.
    """

    @staticmethod
    def _lum(h):
        h = h.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        ch = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        ch = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in ch]
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]

    @classmethod
    def _ratio(cls, a, b):
        l1, l2 = cls._lum(a), cls._lum(b)
        return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)

    @staticmethod
    def _tokens(block):
        import re as _re
        return dict(_re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{3,6})", block))

    def _palette(self, marker):
        import re as _re
        sys.path.insert(0, SCRIPTS)
        import render
        m = _re.search(_re.escape(marker) + r"\{([^}]*)\}", render.CSS)
        self.assertTrue(m, "palette block %s not found" % marker)
        return self._tokens(m.group(1))

    def _assert_aa(self, tokens, grounds):
        text_roles = ["ink", "ink-2", "muted", "accent", "done", "active", "gap", "partial"]
        for role in text_roles:
            fg = tokens.get(role)
            if not fg:
                continue
            for ground in grounds:
                r = self._ratio(fg, ground)
                self.assertGreaterEqual(
                    round(r, 2), 4.5,
                    "--%s (%s) on %s is %.2f:1, below WCAG AA 4.5:1" % (role, fg, ground, r))

    def test_light_palette_meets_aa(self):
        t = self._palette(":root")
        self._assert_aa(t, [t["card"], t["ground"]])

    def test_dark_palette_meets_aa(self):
        t = self._palette(':root[data-theme="dark"]')
        self._assert_aa(t, [t["card"], t["ground"]])


class TestManifests(unittest.TestCase):
    def test_manifests_parse_and_agree(self):
        root = os.path.dirname(os.path.dirname(PLUGIN))
        with open(os.path.join(root, ".claude-plugin", "marketplace.json")) as fh:
            mk = json.load(fh)
        with open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json")) as fh:
            pl = json.load(fh)
        entry = next(p for p in mk["plugins"] if p["name"] == pl["name"])
        self.assertEqual(entry["version"], pl["version"],
                         "marketplace and plugin disagree on version")
        self.assertTrue(os.path.isdir(os.path.join(root, entry["source"])))

    def test_hooks_declare_both_events(self):
        with open(os.path.join(PLUGIN, "hooks", "hooks.json")) as fh:
            h = json.load(fh)
        self.assertEqual(set(h["hooks"]), {"SessionStart", "PreCompact"})
        for ev in h["hooks"].values():
            for group in ev:
                for hook in group["hooks"]:
                    self.assertIn("${CLAUDE_PLUGIN_ROOT}", hook["command"])

    def test_no_third_party_imports(self):
        """Zero dependencies is the promise. Assert it rather than trust it.

        Parsed with ast, not regex: a line of prose beginning "from ..." inside
        a docstring looks exactly like an import to a regex, and the first
        version of this test failed on its own comment.
        """
        import ast as _ast
        # Ask Python what the standard library is rather than maintaining a list
        # by hand. The hand-written version rejected `tempfile` and reported it
        # as "not standard library" -- a test that is wrong AND misleading about
        # why is worse than no test.
        allowed = set(sys.stdlib_module_names) | {"plan_lib", "check", "render", "diagrams"}
        for f in sorted(os.listdir(SCRIPTS)):
            if not f.endswith(".py"):
                continue
            with open(os.path.join(SCRIPTS, f)) as fh:
                tree = _ast.parse(fh.read(), filename=f)
            for node in _ast.walk(tree):
                mods = []
                if isinstance(node, _ast.Import):
                    mods = [a.name for a in node.names]
                elif isinstance(node, _ast.ImportFrom) and node.module:
                    mods = [node.module]
                for mod in mods:
                    self.assertIn(mod.split(".")[0], allowed,
                                  "%s imports %s, which is neither standard library nor a sibling "
                                  "module of this plugin" % (f, mod))


if __name__ == "__main__":
    unittest.main(verbosity=2)
