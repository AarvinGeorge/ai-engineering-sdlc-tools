#!/usr/bin/env python3
"""Tests for plan-layer. Standard library only, like the thing they test.

  python3 tests/test_plan_layer.py

These cover the behaviours that would embarrass the tool in someone else's
repository: talking when uninvited, crashing on a broken plan, passing a check
that tested nothing, and losing a project's own contract keys.
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
        import glob as _glob
        for m in _glob.glob(os.path.join(tempfile.gettempdir(),
                                         "plan-layer-gate-*" + os.path.basename(self.dir) + "*")):
            try:
                os.unlink(m)
            except OSError:
                pass
        shutil.rmtree(self.dir, ignore_errors=True)

    def page(self):
        with open(os.path.join(self.dir, "plan", "index.html")) as fh:
            return fh.read()

    def body(self):
        """The page without its stylesheet. A test asking whether a class was
        USED must not match the rule that merely defines it."""
        return self.page().split('<div class="wrap"', 1)[-1]

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


class TestFigCheck(Base):
    """The two ways a figure goes wrong that are invisible in the source."""

    def write_figures(self, svg, size="12.5"):
        src = ('CSS = "\\n  .dg-lbl{font-size:%spx;fill:#000}\\n"\n'
               'def build(data):\n'
               '    return %%r\n' % size) % (
            '<figure aria-label="a figure">%s</figure>' % svg)
        with open(os.path.join(self.dir, "plan", "figures.py"), "w") as fh:
            fh.write(src)

    def figures(self, svg, size="12.5"):
        self.make_plan()
        self.write_figures(svg, size)
        r = run("render.py", project=self.dir)
        self.assertNotIn("failed to load", r.stdout, "the fixture is not valid Python")
        self.assertIn("aria-label", self.page(), "the fixture figure never rendered")
        return run("figcheck.py", "--no-shots", project=self.dir)

    def test_a_clean_figure_passes(self):
        r = self.figures('<svg viewBox="0 0 400 100">'
                         '<rect x="10" y="10" width="300" height="40"/>'
                         '<text x="20" y="35" class="dg-lbl" text-anchor="start">Short</text>'
                         '</svg>')
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("1 figures checked, 0 problems", r.stdout)

    def test_text_crossing_the_page_edge_fails(self):
        r = self.figures('<svg viewBox="0 0 100 100">'
                         '<text x="10" y="35" class="dg-lbl" text-anchor="start">'
                         'a label far longer than this drawing is wide</text></svg>')
        self.assertEqual(r.returncode, 1)
        self.assertIn("crosses the page edge", r.stdout)

    def test_two_labels_on_one_baseline_fail(self):
        r = self.figures('<svg viewBox="0 0 400 100">'
                         '<text x="20" y="35" class="dg-lbl" text-anchor="start">'
                         'first label here</text>'
                         '<text x="30" y="35" class="dg-lbl" text-anchor="start">'
                         'second label</text></svg>')
        self.assertEqual(r.returncode, 1)
        self.assertIn("overlapping text", r.stdout)

    def test_silent_where_there_is_no_plan(self):
        r = run("figcheck.py", "--no-shots", project=self.dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("no plan", r.stdout)

    def test_font_size_is_read_from_the_page_not_carried_in_the_checker(self):
        """The same label passes at 12.5px and crosses the edge at 40px.

        A checker holding its own copy of the sizes goes stale the first time a
        figure is restyled, and then reports on a drawing nobody has.
        """
        svg = ('<svg viewBox="0 0 200 100"><text x="10" y="35" class="dg-lbl" '
               'text-anchor="start">a modest label</text></svg>')
        self.assertEqual(self.figures(svg).returncode, 0)
        self.write_figures(svg, size="40")
        run("render.py", project=self.dir)
        r = run("figcheck.py", "--no-shots", project=self.dir)
        self.assertEqual(r.returncode, 1, "the size change was not noticed")
        self.assertIn("crosses the page edge", r.stdout)


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

    def test_same_minute_commit_is_not_drift(self):
        """Plan and commit are normally written seconds apart. Reporting that as
        drift trains people to ignore the signal."""
        import subprocess as sp, datetime
        d = self.make_plan()
        d["meta"]["updated"] = datetime.datetime.now(
            datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.write(d)
        run("render.py", project=self.dir)
        with open(os.path.join(self.dir, "src.py"), "w") as fh:
            fh.write("# work\n")
        sp.run(["git", "add", "-A"], cwd=self.dir, capture_output=True)
        sp.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "w"],
               cwd=self.dir, capture_output=True)
        out = run("check.py", project=self.dir).stdout
        self.assertNotIn("newer than meta.updated", out,
                         "a same-minute commit was reported as drift")

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



class TestTasks(Base):
    """An active item may carry a task checklist. Without it the page named a
    plan document and showed nothing of what was in it -- which is how the
    human reading it ends up unable to see the active plan."""

    def _with_tasks(self, tasks, stage="building"):
        d = self.make_plan()
        d["plans"]["now"] = [{"name": "Ship it", "status": "under way",
                              "updated": "2026-01-01", "stage": stage,
                              "plan_file": "p.md", "tasks": tasks}]
        self.write(d)
        return d

    def test_tasks_render_with_a_count(self):
        self._with_tasks([{"name": "Alpha", "state": "done"},
                          {"name": "Beta", "state": "todo"}])
        run("render.py", project=self.dir)
        page = self.page()
        self.assertIn("Alpha", page)
        self.assertIn("Beta", page)
        self.assertIn("1 of 2 done", page)

    def test_bad_state_fails_rather_than_rendering_as_todo(self):
        self._with_tasks([{"name": "Alpha", "state": "in-progress"}])
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("in-progress", r.stdout)

    def test_all_done_but_still_active_is_drift(self):
        self._with_tasks([{"name": "Alpha", "state": "done"}])
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertIn("every task done", r.stdout)

    def test_all_done_at_verified_is_not_drift(self):
        self._with_tasks([{"name": "Alpha", "state": "done"}], stage="verified")
        run("render.py", project=self.dir)
        self.assertNotIn("every task done", run("check.py", project=self.dir).stdout)

    def test_no_tasks_key_renders_nothing_extra(self):
        d = self.make_plan()
        d["plans"]["now"] = [{"name": "Ship it", "status": "s", "updated": "2026-01-01",
                              "stage": "planned"}]
        self.write(d)
        run("render.py", project=self.dir)
        self.assertNotIn('class="tasks"', self.page())


class TestTaskColumns(Base):
    """A checklist someone has to EXECUTE is not prose. Five steps with five
    fields each, rendered as a name and a paragraph, cannot be scanned; the
    person running a manual pass reads one row per step or gives up on the
    page and works from the plan document instead."""

    COLS = [{"key": "tests", "label": "What we are testing for"},
            {"key": "from", "label": "From"},
            {"key": "send", "label": "Send"},
            {"key": "pass", "label": "Pass when"},
            {"key": "how", "label": "How to do it"}]

    def _with_columns(self, tasks, columns=None, stage="building"):
        d = self.make_plan()
        item = {"name": "Run the pass", "status": "under way", "updated": "2026-01-01",
                "stage": stage, "plan_file": "p.md", "tasks": tasks}
        if columns is not None:
            item["task_columns"] = columns
        d["plans"]["now"] = [item]
        self.write(d)
        return d

    def _full_task(self, name="1 book two named people", state="active", **over):
        t = {"name": name, "state": state, "tests": "guests resolve by name",
             "from": "the developer seat", "send": "book a call with Alex and Priya",
             "pass": "both guests on the event", "how": "reply in the same thread"}
        t.update(over)
        return t

    def test_columns_render_as_a_table_with_the_declared_headers_in_order(self):
        self._with_columns([self._full_task()], self.COLS)
        run("render.py", project=self.dir)
        page = self.page()
        body = self.body()
        self.assertIn("ttable", body)
        heads = re.findall(r"<th>(.*?)</th>",
                           body[body.index('<table class="ttable"'):])
        self.assertEqual(heads[:6],
                         ["Step", "What we are testing for", "From", "Send",
                          "Pass when", "How to do it"])

    def test_cells_land_in_their_declared_columns(self):
        self._with_columns([self._full_task()], self.COLS)
        run("render.py", project=self.dir)
        page = self.body()
        row = re.search(r'<tr class="t t--active">(.*?)</tr>', page, re.S).group(1)
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        self.assertEqual(len(cells), 6)
        self.assertIn("book two named people", cells[0])
        self.assertIn("guests resolve by name", cells[1])
        self.assertIn("the developer seat", cells[2])
        self.assertIn("book a call with Alex and Priya", cells[3])
        self.assertIn("both guests on the event", cells[4])
        self.assertIn("reply in the same thread", cells[5])

    def test_a_missing_key_is_an_empty_cell_never_the_word_none(self):
        t = self._full_task()
        del t["how"]
        self._with_columns([t], self.COLS)
        run("render.py", project=self.dir)
        row = re.search(r'<tr class="t t--active">(.*?)</tr>', self.body(), re.S).group(1)
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        self.assertEqual(cells[5].strip(), "")
        self.assertNotIn("None", row)

    def test_a_note_still_renders_under_its_row(self):
        self._with_columns([self._full_task(note="PASS 13 Sep, the event carried both")],
                           self.COLS)
        run("render.py", project=self.dir)
        page = self.body()
        self.assertIn("PASS 13 Sep, the event carried both", page)
        note_row = re.search(r'<tr class="tnoterow[^"]*">(.*?)</tr>', page, re.S).group(1)
        self.assertIn('colspan="6"', note_row)
        self.assertIn("PASS 13 Sep", note_row)
        self.assertLess(page.index('class="t t--active"'), page.index("tnoterow"))

    def test_the_done_count_survives(self):
        self._with_columns([self._full_task(state="done"),
                            self._full_task(name="2 move it", state="todo")], self.COLS)
        run("render.py", project=self.dir)
        self.assertIn("1 of 2 done", self.page())

    def test_each_state_is_still_distinguishable(self):
        self._with_columns([self._full_task(name="a", state="done"),
                            self._full_task(name="b", state="active"),
                            self._full_task(name="c", state="todo")], self.COLS)
        run("render.py", project=self.dir)
        page = self.body()
        for cls in ("t--done", "t--active", "t--todo"):
            self.assertIn('<tr class="t %s">' % cls, page)

    def test_the_table_sits_in_a_container_that_scrolls_sideways(self):
        self._with_columns([self._full_task()], self.COLS)
        run("render.py", project=self.dir)
        page = self.page()
        self.assertRegex(self.body(), r'<div class="tablewrap[^"]*"><table class="ttable"')

    def test_without_columns_the_checklist_is_the_list_it_has_always_been(self):
        self._with_columns([{"name": "Alpha", "state": "done"},
                            {"name": "Beta", "state": "todo", "note": "waiting"}])
        run("render.py", project=self.dir)
        body = self.body()
        self.assertIn('<ol class="tlist">', body)
        self.assertNotIn("ttable", body)
        self.assertIn("waiting", body)

    def test_the_no_columns_markup_is_exactly_what_it_always_was(self):
        """Byte for byte, not merely similar. This capability is worth nothing
        if it moves a single character of the checklist every other plan uses."""
        self._with_columns([{"name": "Alpha", "state": "done", "note": "evidence"},
                            {"name": "Beta", "state": "todo"}])
        run("render.py", project=self.dir)
        block = re.search(r'<div class="tasks">.*?</ol></div>', self.body(), re.S).group(0)
        self.assertEqual(
            block,
            '<div class="tasks"><div class="tcount">1 of 2 done</div>'
            '<ol class="tlist">'
            '<li class="t t--done"><span class="tmark">&#10003;'
            '<span class="sr-only">Done</span></span>'
            '<span class="tname">Alpha</span><span class="tnote">evidence</span></li>'
            '<li class="t t--todo"><span class="tmark">&#183;'
            '<span class="sr-only">Not started</span></span>'
            '<span class="tname">Beta</span></li></ol></div>')

    def test_a_columned_table_prints_no_auto_index(self):
        """A specified checklist's steps carry their own numbers, and its rows
        are listed in the order they will be run rather than in numeric order,
        so an auto index beside the name shows two numbers that disagree."""
        self._with_columns([self._full_task(name="1 the person who asks is a guest"),
                            self._full_task(name="8 invite whoever is copied", state="todo")],
                           self.COLS)
        run("render.py", project=self.dir)
        table = re.search(r'<table class="ttable">.*?</table>', self.body(), re.S).group(0)
        self.assertNotIn("tnum", table)
        self.assertIn("1 the person who asks is a guest", table)
        self.assertIn("8 invite whoever is copied", table)

    def test_the_plain_list_keeps_its_numbering(self):
        self._with_columns([{"name": "Alpha", "state": "done"},
                            {"name": "Beta", "state": "todo"}])
        run("render.py", project=self.dir)
        page = self.page()
        self.assertIn('<ol class="tlist">', self.body())
        self.assertIn("counter-increment:t", page)

    def test_columns_that_are_not_a_list_fail(self):
        self._with_columns([self._full_task()], {"key": "tests"})
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("task_columns", r.stdout)

    def test_a_column_missing_key_or_label_fails(self):
        for bad in ({"label": "No key"}, {"key": "nolabel"}):
            self._with_columns([self._full_task()], [bad])
            run("render.py", project=self.dir)
            r = run("check.py", project=self.dir)
            self.assertEqual(r.returncode, 1, bad)
            self.assertIn("task_columns", r.stdout)

    def test_a_duplicate_column_key_fails(self):
        self._with_columns([self._full_task()],
                           [{"key": "tests", "label": "One"}, {"key": "tests", "label": "Two"}])
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("duplicate", r.stdout)

    def test_a_column_key_colliding_with_a_reserved_task_key_fails(self):
        for key in ("name", "state", "note"):
            self._with_columns([self._full_task()], [{"key": key, "label": "Clash"}])
            run("render.py", project=self.dir)
            r = run("check.py", project=self.dir)
            self.assertEqual(r.returncode, 1, key)
            self.assertIn(key, r.stdout)

    def test_an_unfinished_step_missing_a_declared_column_drifts(self):
        t = self._full_task(name="7 book two named people at once")
        del t["pass"]
        self._with_columns([t], self.COLS)
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertIn("7 book two named people at once", r.stdout)
        self.assertIn("pass", r.stdout)

    def test_a_done_step_missing_a_column_is_exempt(self):
        t = self._full_task(state="done")
        del t["how"]
        self._with_columns([t], self.COLS, stage="verified")
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertNotIn("carries no", r.stdout.replace("carries no evidence", ""))
        self.assertEqual(r.returncode, 0)


class TestTaskResults(Base):
    """`state` says where a step is in the run. `result` says how it turned
    out. A step can be done and have failed, and a page that shows only the
    first cannot be read for the thing the run exists to establish."""

    COLS = [{"key": "send", "label": "Send"}, {"key": "pass", "label": "Pass when"}]

    def _item(self, tasks, columns=None, stage="building"):
        d = self.make_plan()
        item = {"name": "Run the pass", "status": "under way", "updated": "2026-01-01",
                "stage": stage, "plan_file": "p.md", "tasks": tasks}
        if columns is not None:
            item["task_columns"] = columns
        d["plans"]["now"] = [item]
        self.write(d)
        return d

    def _t(self, name="1 book by name", state="done", **over):
        t = {"name": name, "state": state, "send": "book a call", "pass": "both guests on it"}
        t.update(over)
        return t

    def test_a_result_adds_a_leading_column_headed_result(self):
        self._item([self._t(result="pass")], self.COLS)
        run("render.py", project=self.dir)
        body = self.body()
        table = re.search(r'<table class="ttable">.*?</table>', body, re.S).group(0)
        self.assertEqual(re.findall(r"<th>(.*?)</th>", table),
                         ["Result", "Step", "Send", "Pass when"])

    def test_the_result_cell_comes_before_the_step(self):
        self._item([self._t(result="fail")], self.COLS)
        run("render.py", project=self.dir)
        row = re.search(r'<tr class="t t--done">(.*?)</tr>', self.body(), re.S).group(1)
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        self.assertEqual(len(cells), 4)
        self.assertIn("Fail", cells[0])
        self.assertIn("1 book by name", cells[1])

    def test_no_result_anywhere_leaves_the_table_as_it_was(self):
        self._item([self._t()], self.COLS)
        run("render.py", project=self.dir)
        body = self.body()
        table = re.search(r'<table class="ttable">.*?</table>', body, re.S).group(0)
        self.assertEqual(re.findall(r"<th>(.*?)</th>", table),
                         ["Step", "Send", "Pass when"])

    def test_a_task_without_a_result_gets_an_empty_cell(self):
        self._item([self._t(name="a", result="pass"), self._t(name="b")], self.COLS)
        run("render.py", project=self.dir)
        row = re.search(r'<tr class="t t--done"><td[^>]*></td><td class="tstep">'
                        r'.*?b</span>', self.body(), re.S)
        self.assertIsNotNone(row, "the resultless step did not get an empty leading cell")
        self.assertNotIn("None", self.body())

    def test_the_four_outcomes_carry_a_word_and_a_mark(self):
        self._item([self._t(name="a", result="pass"), self._t(name="b", result="fail"),
                    self._t(name="c", result="covered"),
                    self._t(name="d", result="blocked", state="blocked")], self.COLS)
        run("render.py", project=self.dir)
        body = self.body()
        for value, word in (("pass", "Pass"), ("fail", "Fail"),
                            ("covered", "Covered"), ("blocked", "Blocked")):
            m = re.search(r'<span class="res res--%s">(.*?)</span></td>' % value, body)
            self.assertIsNotNone(m, value)
            inner = m.group(1)
            self.assertIn(word, inner)
            mark = inner.replace(word, "").strip()
            self.assertTrue(mark, "%s carries no mark, only colour and a word" % value)

    def test_an_unknown_result_renders_plainly_rather_than_disappearing(self):
        self._item([self._t(result="needs a second run")], self.COLS)
        run("render.py", project=self.dir)
        self.assertIn("needs a second run", self.body())

    def test_the_step_keeps_its_own_state_marker(self):
        self._item([self._t(result="fail")], self.COLS)
        run("render.py", project=self.dir)
        step = re.search(r'<td class="tstep">(.*?)</td>', self.body(), re.S).group(1)
        self.assertIn('class="tmark"', step)

    def test_the_note_row_spans_the_result_column_too(self):
        self._item([self._t(result="pass", note="ran at 16:51")], self.COLS)
        run("render.py", project=self.dir)
        self.assertIn('colspan="4"', self.body())

    def test_a_result_shows_in_the_plain_list_as_well(self):
        self._item([self._t(result="fail")])
        run("render.py", project=self.dir)
        body = self.body()
        self.assertIn('<ol class="tlist">', body)
        self.assertIn('res res--fail', body)

    def test_a_result_that_is_not_a_string_fails(self):
        self._item([self._t(result=["pass"])], self.COLS)
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("result", r.stdout)


class TestNoteShapes(Base):
    """A result's story is usually the time it ran and then what happened. Two
    short points read faster than one dense paragraph, so a note may be a
    list."""

    def _item(self, tasks, columns=None):
        d = self.make_plan()
        item = {"name": "Run the pass", "status": "under way", "updated": "2026-01-01",
                "stage": "building", "plan_file": "p.md", "tasks": tasks}
        if columns is not None:
            item["task_columns"] = columns
        d["plans"]["now"] = [item]
        self.write(d)
        return d

    COLS = [{"key": "send", "label": "Send"}]

    def test_a_list_note_renders_as_bullets_in_the_table(self):
        self._item([{"name": "a", "state": "done", "send": "x",
                     "note": ["PASS 13 Sep 16:51 UTC", "both guests landed on the event"]}],
                   self.COLS)
        run("render.py", project=self.dir)
        note = re.search(r'<tr class="tnoterow[^"]*">(.*?)</tr>', self.body(), re.S).group(1)
        self.assertIn("<ul", note)
        self.assertEqual(note.count("<li>"), 2)
        self.assertIn("PASS 13 Sep 16:51 UTC", note)
        self.assertIn("both guests landed on the event", note)

    def test_a_list_note_renders_as_bullets_in_the_plain_list(self):
        self._item([{"name": "a", "state": "done",
                     "note": ["ran at 16:51", "the event carried both"]}])
        run("render.py", project=self.dir)
        block = re.search(r'<div class="tasks">.*?</ol></div>', self.body(), re.S).group(0)
        self.assertIn("<ul", block)
        self.assertEqual(block.count("<li>"), 2)
        self.assertIn("the event carried both", block)

    def test_a_string_note_is_byte_for_byte_what_it_always_was(self):
        self._item([{"name": "Alpha", "state": "done", "note": "evidence"},
                    {"name": "Beta", "state": "todo"}])
        run("render.py", project=self.dir)
        block = re.search(r'<div class="tasks">.*?</ol></div>', self.body(), re.S).group(0)
        self.assertEqual(
            block,
            '<div class="tasks"><div class="tcount">1 of 2 done</div>'
            '<ol class="tlist">'
            '<li class="t t--done"><span class="tmark">&#10003;'
            '<span class="sr-only">Done</span></span>'
            '<span class="tname">Alpha</span><span class="tnote">evidence</span></li>'
            '<li class="t t--todo"><span class="tmark">&#183;'
            '<span class="sr-only">Not started</span></span>'
            '<span class="tname">Beta</span></li></ol></div>')

    def test_a_note_that_is_neither_a_string_nor_a_list_of_strings_fails(self):
        for bad in (7, {"a": 1}, ["fine", 9]):
            self._item([{"name": "a", "state": "done", "note": bad}])
            run("render.py", project=self.dir)
            r = run("check.py", project=self.dir)
            self.assertEqual(r.returncode, 1, bad)
            self.assertIn("note", r.stdout)

    def test_a_string_note_still_passes_the_gate(self):
        self._item([{"name": "a", "state": "done", "note": "plain prose"}])
        run("render.py", project=self.dir)
        self.assertNotIn("note must", run("check.py", project=self.dir).stdout)


class TestStaleness(Base):
    """The page disagreeing with ITSELF is detectable, and it is what actually
    rotted. Structure was never the problem."""

    def _active(self, **over):
        d = self.make_plan()
        item = {"name": "Ship it", "status": "under way", "updated": "2026-01-01",
                "stage": "building", "plan_file": "p.md", "capability": 1,
                "tasks": [{"name": "Alpha", "state": "done"}]}
        item.update(over)
        d["plans"]["now"] = [item]
        self.write(d)
        return d

    def test_not_yet_language_with_done_tasks_fails(self):
        self._active(status="Built and waiting for its first real message.")
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("contradicts itself", r.stdout)

    def test_not_yet_language_without_done_tasks_is_fine(self):
        self._active(status="Waiting for its first real message.", tasks=[])
        run("render.py", project=self.dir)
        self.assertNotIn("contradicts itself", run("check.py", project=self.dir).stdout)

    def test_capability_not_started_while_active_fails(self):
        d = self._active()
        d["capabilities"][0]["build"] = "not-started"
        d["capabilities"][0]["evidence"] = ""
        self.write(d)
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("while an active item works on it", r.stdout)

    def test_insider_shorthand_fails(self):
        d = self.make_plan()
        d["orientation"]["shape"] = "It is a Tuesday, obviously."
        self.write(d)
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("shorthand", r.stdout)

    def test_undefined_jargon_drifts(self):
        d = self.make_plan()
        d["orientation"]["why"] = "We rely on Quantum Flux Routing to do this."
        d["glossary"] = [{"term": "Tenant", "def": "one customer"}]
        self.write(d)
        run("render.py", project=self.dir)
        self.assertIn("not in the glossary", run("check.py", project=self.dir).stdout)

    def test_clean_plan_stays_clean(self):
        """The template must not trip its own new checks."""
        self.make_plan()
        run("render.py", project=self.dir)
        out = run("check.py", project=self.dir).stdout
        for phrase in ("contradicts itself", "shorthand"):
            self.assertNotIn(phrase, out)


class TestOneThingAtATime(Base):
    """The page answers "what is happening right now" in one glance, or it does not."""

    def two_active(self):
        d = self.make_plan()
        d["plans"]["now"] = [
            {"name": "First", "status": "going", "updated": "2026-01-01", "stage": "planned"},
            {"name": "Second", "status": "also going", "updated": "2026-01-01",
             "stage": "planned"},
        ]
        return d

    def test_a_second_active_item_fails(self):
        self.write(self.two_active())
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("more than one item", r.stdout)

    def test_a_project_may_declare_that_it_runs_several(self):
        d = self.two_active()
        d["meta"]["allow_multiple_active"] = True
        self.write(d)
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("more than one item", r.stdout)

    def test_one_active_item_is_quiet(self):
        d = self.make_plan()
        d["plans"]["now"] = [{"name": "First", "status": "going",
                              "updated": "2026-01-01", "stage": "planned"}]
        self.write(d)
        run("render.py", project=self.dir)
        self.assertNotIn("more than one item", run("check.py", project=self.dir).stdout)


class TestFinishedPlans(Base):
    """A finished plan nobody can date or read the result of is a name in a list."""

    def done_entry(self, **entry):
        d = self.make_plan()
        d["plans"]["done"] = [entry]
        self.write(d)
        run("render.py", project=self.dir)
        return run("check.py", project=self.dir)

    def test_a_finished_plan_with_no_period_drifts(self):
        r = self.done_entry(name="Staging", outcome="It runs.")
        self.assertEqual(r.returncode, 0, "an undated record is drift, not a failure")
        self.assertIn("no period", r.stdout)

    def test_a_finished_plan_with_no_outcome_drifts(self):
        r = self.done_entry(name="Staging", period="28 Jul to 2 Aug")
        self.assertIn("says nothing about what it produced", r.stdout)

    def test_a_carried_over_status_counts_as_the_outcome(self):
        """Items are moved rather than rewritten, so the active field name
        arrives with them and the page already reads it in that slot."""
        r = self.done_entry(name="Staging", period="28 Jul to 2 Aug",
                            status="Container answers on 18889.")
        self.assertNotIn("says nothing about what it produced", r.stdout)

    def test_a_complete_entry_is_quiet(self):
        r = self.done_entry(name="Staging", period="28 Jul to 2 Aug", outcome="It runs.")
        self.assertNotIn("no period", r.stdout)
        self.assertNotIn("says nothing about what it produced", r.stdout)


class TestTwoVersionFields(Base):
    def test_a_legacy_version_that_disagrees_drifts(self):
        d = self.make_plan()
        d["meta"]["version"] = "0.0.9"
        self.write(d)
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertEqual(r.returncode, 0, "a legacy field is drift, not a failure")
        self.assertIn("meta.version", r.stdout)

    def test_a_legacy_version_that_agrees_is_quiet(self):
        d = self.make_plan()
        d["meta"]["version"] = d["meta"]["plan_version"]
        self.write(d)
        run("render.py", project=self.dir)
        self.assertNotIn("meta.version", run("check.py", project=self.dir).stdout)


class TestDependencies(Base):
    """"This waits on that" has to be data. Written only in prose, nothing can check it —
    which is how an item stayed active for three days while its blocker sat unstarted."""

    def _pair(self, dep_bucket):
        d = self.make_plan()
        dep = {"name": "Do this first", "why": "w", "unblocks": "u", "stage": "planned"}
        item = {"name": "Do this second", "status": "s", "updated": "2026-01-01",
                "stage": "building", "plan_file": "p.md",
                "tasks": [{"name": "A", "state": "active"}],
                "blocked_by": ["Do this first"]}
        d["plans"]["now"] = [item]
        d["plans"].setdefault(dep_bucket, []).insert(0, dep)
        self.write(d)
        return d

    def test_active_item_waiting_on_a_merely_queued_item_fails(self):
        self._pair("next")
        run("render.py", project=self.dir)
        r = run("check.py", project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("in the wrong place", r.stdout)

    def test_dependency_that_does_not_exist_fails(self):
        d = self.make_plan()
        d["plans"]["now"] = [{"name": "X", "status": "s", "updated": "2026-01-01",
                              "stage": "planned", "blocked_by": ["nothing named this"]}]
        self.write(d)
        run("render.py", project=self.dir)
        self.assertIn("not on the plan at all", run("check.py", project=self.dir).stdout)

    def test_all_unfinished_tasks_blocked_drifts(self):
        d = self.make_plan()
        d["plans"]["now"] = [{"name": "X", "status": "s", "updated": "2026-01-01",
                              "stage": "building", "plan_file": "p.md",
                              "tasks": [{"name": "A", "state": "done"},
                                        {"name": "B", "state": "blocked"}]}]
        self.write(d)
        run("render.py", project=self.dir)
        self.assertIn("nothing that can move", run("check.py", project=self.dir).stdout)

    def test_no_blocked_by_key_is_fine(self):
        self.make_plan()
        run("render.py", project=self.dir)
        self.assertNotIn("waits on", run("check.py", project=self.dir).stdout)

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


class TestGateHook(Base):
    """The Stop hook must be impossible to get trapped by."""

    def _hook(self, session=None):
        """Always a fresh session id: the hook deliberately blocks only once per
        session+failure, so a reused id would make the second test see silence
        left over from the first."""
        sid = session or ("t-" + os.path.basename(self.dir))
        return run("gate_hook.py", project=self.dir,
                   stdin=json.dumps({"session_id": sid}))

    def _hook_raw(self, payload):
        return run("gate_hook.py", project=self.dir, stdin=payload)

    def test_blocks_when_the_gate_fails(self):
        d = self.make_plan()
        d["capabilities"][0].update(build="done", evidence="")
        self.write(d)
        run("render.py", project=self.dir)
        out = json.loads(self._hook().stdout)
        self.assertEqual(out["decision"], "block")
        self.assertIn("no evidence", out["reason"])

    def test_silent_when_the_gate_passes(self):
        self.make_plan()
        run("render.py", project=self.dir)
        out = self._hook()
        payload = json.loads(out.stdout) if out.stdout.strip() else {}
        # Never blocks, and never invents a failure.
        self.assertNotIn("decision", payload)
        self.assertNotIn("reason", payload)

    def test_silent_where_there_is_no_plan(self):
        self.assertEqual(self._hook().stdout.strip(), "")

    def test_honours_stop_hook_active(self):
        """The harness sets this when it is already re-running us. Ignoring it
        is how a Stop hook becomes an infinite loop."""
        d = self.make_plan()
        d["capabilities"][0].update(build="done", evidence="")
        self.write(d)
        run("render.py", project=self.dir)
        out = self._hook_raw(json.dumps({"stop_hook_active": True,
                                         "session_id": "t-" + os.path.basename(self.dir)}))
        self.assertEqual(out.stdout.strip(), "", "blocked despite stop_hook_active")

    def test_does_not_block_twice_for_the_same_failure(self):
        d = self.make_plan()
        d["capabilities"][0].update(build="done", evidence="")
        self.write(d)
        run("render.py", project=self.dir)
        sid = "once-" + os.path.basename(self.dir)
        first = self._hook(sid)
        second = self._hook(sid)
        self.assertIn("block", first.stdout)
        self.assertEqual(second.stdout.strip(), "",
                         "same failure raised twice — that is nagging, not a gate")

    def test_drift_alone_never_blocks(self):
        """Drift fires during ordinary work. A hook that interrupts every turn
        gets switched off."""
        import subprocess as sp
        self.make_plan()
        run("render.py", project=self.dir)
        with open(os.path.join(self.dir, "unrelated.py"), "w") as fh:
            fh.write("# work in progress\n")
        sp.run(["git", "add", "-A"], cwd=self.dir, capture_output=True)
        out = self._hook("drift-" + os.path.basename(self.dir))
        # The invariant is that drift never BLOCKS. Since 0.9.1 it may still be
        # reported to the human, which is the point of that release -- silence
        # was how staleness went unnoticed for days.
        payload = json.loads(out.stdout) if out.stdout.strip() else {}
        self.assertNotEqual(payload.get("decision"), "block",
                            "blocked on drift: %s" % out.stdout[:120])

    def test_a_broken_gate_never_traps_the_session(self):
        os.makedirs(os.path.join(self.dir, "plan"), exist_ok=True)
        with open(os.path.join(self.dir, "plan", "plan.json"), "w") as fh:
            fh.write("{ not json")
        r = self._hook()
        self.assertEqual(r.returncode, 0)


    def test_staleness_is_reported_to_the_human(self):
        """0.9.1: silence is what let staleness sit unnoticed for days."""
        d = self.make_plan()
        d["orientation"]["why"] = "We rely on Quantum Flux Routing for this."
        d["glossary"] = [{"term": "Tenant", "def": "one customer"}]
        self.write(d)
        run("render.py", project=self.dir)
        out = self._hook()
        payload = json.loads(out.stdout) if out.stdout.strip() else {}
        self.assertIn("systemMessage", payload)
        self.assertNotEqual(payload.get("decision"), "block")

    def test_work_in_progress_drift_stays_quiet(self):
        """Uncommitted files fire constantly mid-task. A notice that is always
        there is one nobody reads."""
        import importlib, sys
        sys.path.insert(0, os.path.join(PLUGIN, "scripts"))
        gh = importlib.import_module("gate_hook")
        self.assertFalse(gh._is_staleness("3 uncommitted file(s) outside plan/ but the plan is untouched"))
        self.assertTrue(gh._is_staleness("plan.json last updated 20 days ago"))

class TestDurability(Base):
    """The source of truth must survive an interrupted write."""

    def test_interrupted_write_leaves_the_original_intact(self):
        import plan_lib as L
        self.make_plan()
        p = os.path.join(self.dir, "plan", "plan.json")
        before = open(p).read()

        class Boom(Exception):
            pass

        real = L.os.replace

        def explode(a, b):
            raise Boom("interrupted just before the rename")

        L.os.replace = explode
        try:
            with self.assertRaises(Boom):
                L.atomic_write(p, "TOTAL GARBAGE")
        finally:
            L.os.replace = real

        self.assertEqual(open(p).read(), before,
                         "an interrupted write damaged the file it was replacing")
        json.loads(open(p).read())          # still parseable

    def test_no_temp_files_are_left_behind(self):
        import plan_lib as L
        self.make_plan()
        p = os.path.join(self.dir, "plan", "plan.json")
        L.atomic_write(p, '{"ok": true}\n')
        leftovers = [f for f in os.listdir(os.path.dirname(p)) if f.startswith(".plan-layer-")]
        self.assertEqual(leftovers, [], "temp files left in the plan directory")
        self.assertEqual(json.load(open(p)), {"ok": True})

    def test_page_is_written_atomically(self):
        """A concurrent reader must never see a partial page."""
        self.make_plan()
        run("render.py", project=self.dir)
        page = self.page()
        self.assertTrue(page.rstrip().endswith("</div>"),
                        "page looks truncated: %r" % page[-40:])
        self.assertIn("data-fingerprint=", page)


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
        self.assertEqual(set(h["hooks"]), {"SessionStart", "PreCompact", "Stop"})
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



class TestLegend(Base):
    """The page prints a key, and the key must cover the page.

    Nine status vocabularies were being painted with nothing declaring any of
    them, which is also how they drifted into each other -- "Planned" and
    "Done" both green, "at risk" and "broken" identical, "No plan" and "No plan
    written yet" for one state. The legend is generated from the same maps the
    sections render from; this test asserts that structural guarantee actually
    holds in the output, and it is proven able to fail before being trusted.
    """

    @staticmethod
    def _labels(fragment, include_spoken=True):
        """Every state word this fragment paints.

        Pills and stage chips now contain a nested dot span and a spoken label,
        so the inner markup is removed before the outer text is read.
        """
        import re
        spoken = re.findall(r'<span class="sr-only">(.*?)</span>', fragment)
        frag = re.sub(r'<span class="sr-only">.*?</span>', "", fragment)
        frag = re.sub(r'<span class="dot"[^>]*></span>', "", frag)
        chips = re.findall(r'<span class="(?:pill|stage|lgtxt|lgcard)[^"]*">(.*?)</span>',
                           frag)
        words = set(chips) | (set(spoken) if include_spoken else set())
        return {w.strip().rstrip(":").strip() for w in words if w.strip()}

    @classmethod
    def _split(cls, page):
        """The key, and everything that is not the key."""
        i = page.find('<div class="legend">')
        if i == -1:
            return "", page
        j = page.find("<h2>", i)          # the key runs to the next section
        return page[i:j], page[:i] + page[j:]

    def _every_state(self):
        d = self.make_plan()
        d["capabilities"] = [
            {"id": 1, "name": "Alpha", "build": "done", "plan": "planned",
             "evidence": "shipped"},
            {"id": 2, "name": "Beta", "build": "active", "plan": "partial",
             "evidence": "under way"},
            {"id": 3, "name": "Gamma", "build": "partial", "plan": "none",
             "evidence": "half"},
            {"id": 4, "name": "Delta", "build": "not-started", "plan": "none"},
        ]
        d["plans"] = {
            "done": [{"name": "Finished", "period": "Jan", "tasks": "2 tasks",
                      "outcome": "did it", "file": "a.md"}],
            "now": [{"name": "Doing", "stage": "building", "capability": 2,
                     "plan_file": "b.md", "status": "under way", "updated": "2026-01-01",
                     "tasks": [{"name": "one", "state": "done"},
                               {"name": "two", "state": "active"},
                               {"name": "three", "state": "blocked"},
                               {"name": "four", "state": "todo"}]}],
            "next": [{"name": "Later", "stage": "intent", "capability": 3,
                      "why": "because"}],
        }
        d["edge_cases"] = [
            {"id": "E1", "case": "a", "surface": "mail", "status": "open",
             "mitigation": "m"},
            {"id": "E2", "case": "b", "surface": "mail", "status": "mitigated",
             "mitigation": "m"},
            {"id": "E3", "case": "c", "surface": "mail", "status": "accepted",
             "mitigation": "reasoned"},
        ]
        d["invariants"] = [
            {"rule": "One", "state": "holding", "detail": "d"},
            {"rule": "Two", "state": "at risk", "detail": "d"},
            {"rule": "Three", "state": "broken", "detail": "d"},
        ]
        self.write(d)
        run("render.py", project=self.dir)
        return self.page()

    def test_every_state_the_page_paints_is_in_the_key(self):
        key, body = self._split(self._every_state())
        self.assertTrue(key, "no legend was rendered")
        missing = self._labels(body) - self._labels(key)
        self.assertEqual(missing, set(),
                         "painted on the page but absent from the key: %s" % sorted(missing))

    def test_the_check_can_fail(self):
        """A test that cannot fail proves nothing. Plant a state and confirm."""
        page = self._every_state()
        planted = page.replace('<h2>Glossary',
                               '<span class="pill s-gap">Invented state</span><h2>Glossary', 1)
        if planted == page:                       # no glossary in the template
            planted = page.replace("</div>",
                                   '<span class="pill s-gap">Invented state</span></div>', 1)
        key, body = self._split(planted)
        self.assertIn("Invented state", self._labels(body) - self._labels(key))

    def test_three_invariant_states_render_three_ways(self):
        page = self._every_state()
        for word in ("Holding", "At risk", "Broken"):
            self.assertIn(">%s</span>" % word, page)
        # the old code painted anything that was not holding in one colour
        self.assertNotIn("inv--warn", page)

    def test_planned_is_not_painted_as_done(self):
        page = self._every_state()
        self.assertIn('class="pill s-plan"', page)
        self.assertNotIn('<span class="pill s-done">Planned</span>', page)

    def test_the_live_dot_marks_only_work_in_progress(self):
        page = self._every_state()
        import re
        # a dot may only appear inside something that also says it is live
        for m in re.finditer(r'<span class="(?:pill|stage)([^"]*)">'
                             r'<span class="dot"[^>]*></span>(.*?)</span>', page):
            self.assertIn(m.group(2).strip(), ("In progress", "Building"),
                          "a live dot on %r, which does not mean work in flight"
                          % m.group(2))
        self.assertIn('<span class="dot"', page)

    def test_reduced_motion_keeps_the_dot_and_drops_the_ring(self):
        page = self._every_state()
        self.assertIn("prefers-reduced-motion:reduce", page)
        i = page.find("prefers-reduced-motion:reduce")
        block = page[i:i + 120]
        self.assertIn(".dot::after", block)
        self.assertIn("animation:none", block)

    def test_no_key_when_there_is_nothing_to_key(self):
        d = self.make_plan()
        for k in ("capabilities", "edge_cases", "invariants", "plans", "cycle"):
            d.pop(k, None)
        self.write(d)
        run("render.py", project=self.dir)
        self.assertNotIn('<div class="legend">', self.page())


class TestDonePlanShapes(Base):
    """A finished plan is MOVED, not rewritten, so it arrives in either shape.

    Rendering only one of them printed a Python repr of a list of task dicts --
    roughly 1,100 characters -- onto the page, and silently dropped the item's
    link and its entire explanation.
    """

    def _done(self, item):
        d = self.make_plan()
        d["plans"] = {"done": [item], "now": [], "next": []}
        self.write(d)
        run("render.py", project=self.dir)
        return self.page()

    def test_a_moved_item_does_not_print_a_python_repr(self):
        page = self._done({"name": "Run", "status": "stopped at 8 of 12",
                           "plan_file": "35.md",
                           "tasks": [{"name": "case one", "state": "done"},
                                     {"name": "case two", "state": "todo"}]})
        self.assertNotIn("'state':", page)
        self.assertNotIn("[{", page)
        self.assertIn("1 of 2 done", page)
        self.assertIn("case one", page)

    def test_a_moved_item_keeps_its_link_and_its_explanation(self):
        page = self._done({"name": "Run", "status": "stopped at 8 of 12",
                           "plan_file": "35.md", "tasks": []})
        self.assertIn("35.md", page)
        self.assertIn("stopped at 8 of 12", page)

    def test_the_original_shape_is_unchanged(self):
        page = self._done({"name": "Run", "period": "Jan 2026", "tasks": "4 tasks",
                           "outcome": "it worked", "notable": "lesson", "file": "a.md"})
        self.assertIn("Jan 2026 · 4 tasks", page)
        self.assertIn("it worked", page)
        self.assertIn("lesson", page)
        self.assertIn("a.md", page)
        self.assertNotIn('class="tasks"', page)


if __name__ == "__main__":
    unittest.main(verbosity=2)
