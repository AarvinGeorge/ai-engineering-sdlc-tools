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
        allowed = {"json", "os", "sys", "subprocess", "hashlib", "html", "datetime",
                   "importlib", "plan_lib", "check", "re", "time"}
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
                                  "%s imports %s, which is not standard library" % (f, mod))


if __name__ == "__main__":
    unittest.main(verbosity=2)
