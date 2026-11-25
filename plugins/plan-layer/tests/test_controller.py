"""Tracker controller (0.19.0): one writer, the diff as data, rules on events."""
import json
import os
import subprocess
import sys
import unittest
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_light_and_budget import Base, PLUGIN, SCRIPTS, run  # noqa: E402
import plan_lib as L  # noqa: E402


def item(name, stage="intent", **kw):
    d = {"name": name, "why": "w", "unblocks": "u", "stage": stage, "plan_file": None}
    d.update(kw)
    return d


def ctl(msgs):
    return [m for m in msgs if "move.py" in m or "meta.controller" in m or "by hand" in m]


class ControllerBase(Base):
    def setUp(self):
        super().setUp()
        self.d["meta"]["naming"] = "work-ids"
        self.d["meta"]["controller"] = {"one_writer": True}
        self.d["plans"]["now"] = [item("E-01.S2 Login page", "building", plan_file="docs/p.md",
                                       status="wiring the form", updated="2026-01-01",
                                       tasks=[{"name": "E-01.S2.T1 form", "state": "todo"}])]
        self.d["plans"]["next"] = [item("E-01.S3 Logout page")]
        self.d["plans"]["done"] = []

    def move(self, *args):
        return run("move.py", *args, project=self.dir)

    def stamp(self):
        p = os.path.join(self.dir, "plan", "controller-state.json")
        return json.load(open(p)) if os.path.isfile(p) else None


class TestPlumbing(ControllerBase):
    def test_config_absent_is_off(self):
        del self.d["meta"]["controller"]
        self.assertEqual(L.controller_config(self.d), (None, None))

    def test_config_defaults(self):
        cfg, err = L.controller_config(self.d)
        self.assertIsNone(err)
        self.assertEqual(cfg, {"one_writer": True, "base": "main", "decision_log": None, "rules": []})

    def test_config_faults_are_words(self):
        for bad, word in (([], "object"), ({"one_writer": "yes"}, "true or false"),
                          ({"surprise": 1}, "unknown"), ({"base": ""}, "base"),
                          ({"rules": {}}, "rules")):
            self.d["meta"]["controller"] = bad
            cfg, err = L.controller_config(self.d)
            self.assertIsNone(cfg, bad)
            self.assertIn(word, err, bad)

    def test_one_writer_needs_work_id_naming(self):
        del self.d["meta"]["naming"]
        cfg, err = L.controller_config(self.d)
        self.assertIn("work-ids", err)

    def test_controlled_reads_bucket_stage_tasks_and_releases_not_status(self):
        self.d["releases"] = [{"id": "R-01", "name": "R-01 Accounts", "stage": "build",
                               "stories": ["E-01.S2"]}]
        c = L.controlled(self.d)
        s2 = c["items"]["E-01.S2"]
        self.assertEqual(s2, {"bucket": "now", "stage": "building",
                              "tasks": {"E-01.S2.T1 form": "todo"}})
        self.assertEqual(c["releases"], {"R-01": "build"})

    def test_duplicate_live_work_ids_are_found(self):
        self.assertEqual(L.duplicate_ids(self.d), [])
        self.d["plans"]["next"].append(item("E-01.S2 Login page, again"))
        self.assertEqual(L.duplicate_ids(self.d), ["E-01.S2"])

    def test_write_stamp_round_trips_and_keeps_other_keys(self):
        self.write()
        path = L.controller_state_path(self.dir)
        with open(path, "w") as fh:
            json.dump({"adopted": [{"at": "x"}]}, fh)
        L.write_stamp(self.dir, self.d, "move.py E-01.S2 --stage building")
        st = L.controller_state(self.dir)
        self.assertEqual(st["adopted"], [{"at": "x"}])
        self.assertEqual(st["writes"]["by"], "move.py E-01.S2 --stage building")
        self.assertEqual(st["writes"]["items"], L.controlled(self.d)["items"])
        self.assertTrue(st["writes"]["at"].endswith("Z"))

    def test_writer_matrix_names_every_stamped_field(self):
        fields = " ".join(w["field"] for w in L.WRITERS)
        for f in ("stage", "tasks[].state", "releases[].stage", "meta.paused",
                  "plan/tracker-state.json", "plan/controller-state.json"):
            self.assertIn(f, fields)
        for w in L.WRITERS:
            self.assertTrue(w["writer"] and w["enforced"], w)


class TestFixRound1(ControllerBase):
    def test_write_stamp_refuses_an_unreadable_record(self):
        self.write()
        with open(L.controller_state_path(self.dir), "w") as fh:
            fh.write("{not json")
        with self.assertRaises(ValueError) as cm:
            L.write_stamp(self.dir, self.d, "move.py x")
        self.assertIn("unreadable", str(cm.exception))
        self.assertEqual(open(L.controller_state_path(self.dir)).read(), "{not json")

    def test_release_keys_are_work_ids_not_raw_ids(self):
        self.d["releases"] = [
            {"id": "R-1", "name": "n", "stage": "build"},
            {"id": "R-01 Accounts", "name": "n", "stage": "gate"},
            {"id": "R-02-hotfix", "name": "n", "stage": "build"}]
        self.assertEqual(L.controlled(self.d)["releases"], {"R-01": "gate", "R-02": "build"})

    def test_schema_release_id_pattern_is_strict(self):
        import re
        schema = json.load(open(os.path.join(PLUGIN, "schema", "plan.schema.json")))
        pat = schema["properties"]["releases"]["items"]["properties"]["id"]["pattern"]
        self.assertEqual(pat, "^R-[0-9]{2,}$")
        self.assertTrue(re.match(pat, "R-01"))
        for bad in ("R-1", "R-01 Accounts", "R-02-hotfix"):
            self.assertFalse(re.match(pat, bad), bad)

    def test_meta_not_an_object_is_off_and_base_is_trimmed(self):
        self.d["meta"] = "oops"
        self.assertEqual(L.controller_config(self.d), (None, None))
        self.d["meta"] = {"naming": "work-ids", "controller": {"base": " main "}}
        self.assertEqual(L.controller_config(self.d)[0]["base"], "main")


def stamp_now(test):
    """Stamp the plan as move.py would, without move.py (Task 3 builds it)."""
    test.write()
    L.write_stamp(test.dir, test.d, "test")


class TestOneWriterGate(ControllerBase):
    def test_off_without_controller(self):
        del self.d["meta"]["controller"]
        self.write()
        _, fails, drifts = self.gate()
        self.assertEqual(ctl(fails + drifts), [])

    def test_on_without_stamp_fails_and_says_adopt(self):
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue(any("move.py --adopt" in f for f in fails), fails)

    def test_clean_after_stamp(self):
        stamp_now(self)
        _, fails, _ = self.gate()
        self.assertEqual(ctl(fails), [], fails)

    def test_hand_edit_of_stage_fails_naming_item_field_and_writer(self):
        stamp_now(self)
        self.d["plans"]["now"][0]["stage"] = "verified"
        self.write()
        rc, fails, _ = self.gate()
        self.assertEqual(rc, 1)
        hit = [f for f in fails if "E-01.S2" in f and "stage" in f and "by hand" in f]
        self.assertTrue(hit, fails)
        self.assertIn("revert the hand edit, or run move.py --adopt", hit[0])

    def test_hand_edit_of_task_state_fails_but_prose_status_is_free(self):
        stamp_now(self)
        self.d["plans"]["now"][0]["status"] = "rewritten by hand"
        self.write()
        _, fails, _ = self.gate()
        self.assertEqual(ctl(fails), [], "prose status is not controlled (ruling 2)")
        self.d["plans"]["now"][0]["tasks"][0]["state"] = "done"
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue(any("E-01.S2.T1 form" in f and "done" in f for f in fails), fails)

    def test_two_live_items_with_one_work_id_fail(self):
        stamp_now(self)
        self.d["plans"]["next"].append(item("E-01.S2 Login page, again"))
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue(any("E-01.S2" in f and "rename the duplicate" in f for f in fails), fails)

    def test_json_has_no_controller_key_when_off(self):
        del self.d["meta"]["controller"]
        self.write()
        run("render.py", project=self.dir)
        out = json.loads(run("check.py", "--json", project=self.dir).stdout)
        self.assertNotIn("controller", out)
        self.assertNotIn("controller", out["summary"])

    def test_a_crash_inside_the_controller_is_a_fail_not_silence(self):
        stamp_now(self)
        with open(L.controller_state_path(self.dir), "w") as fh:
            json.dump({"writes": {"items": {"E-01.S2": "not-a-dict"}}}, fh)
        _, fails, _ = self.gate()
        self.assertTrue(any("check crashed" in f for f in fails), fails)

    def test_new_idea_in_next_at_first_stage_is_planning_not_a_hand_move(self):
        stamp_now(self)
        self.d["plans"]["next"].append(item("E-01.S4 Profile page"))
        self.write()
        _, fails, _ = self.gate()
        self.assertEqual(ctl(fails), [], fails)

    def test_new_item_straight_into_now_fails(self):
        stamp_now(self)
        self.d["plans"]["now"].append(item("E-02.S1 Search", "building", status="s", updated="u",
                                           plan_file="docs/q.md"))
        self.d["meta"]["allow_multiple_active"] = True
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue(any("E-02.S1" in f and "plans.now" in f for f in fails), fails)

    def test_hand_move_to_done_fails_but_a_roll_does_not(self):
        stamp_now(self)
        s2 = self.d["plans"]["now"].pop(0)
        self.d["plans"]["done"].append({"name": s2["name"], "period": "2026-01-02", "outcome": "o"})
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue(any("E-01.S2" in f and "left" in f for f in fails), fails)
        os.makedirs(os.path.join(self.dir, "plan", "archive"), exist_ok=True)
        with open(os.path.join(self.dir, "plan", "archive", "done.json"), "w") as fh:
            json.dump([{"name": s2["name"]}], fh)
        self.d["plans"]["done"] = []
        self.write()
        _, fails, _ = self.gate()
        self.assertEqual([f for f in fails if "E-01.S2" in f and "left" in f], [], fails)

    def test_release_stage_hand_edit_fails(self):
        self.d["releases"] = [{"id": "R-01", "name": "R-01 Accounts", "stage": "build", "stories": []}]
        stamp_now(self)
        self.d["releases"][0]["stage"] = "production"
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue(any("R-01" in f and "move.py --adopt" in f for f in fails), fails)

    def test_bad_config_is_a_fail(self):
        self.d["meta"]["controller"] = {"one_writer": "yes"}
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue(any("meta.controller.one_writer" in f for f in fails), fails)

    def test_json_output_carries_structured_findings(self):
        self.write()
        run("render.py", project=self.dir)
        r = run("check.py", "--json", project=self.dir)
        out = json.loads(r.stdout)
        self.assertTrue(any(f["check"] == "one_writer" and f["level"] == "FAIL"
                            for f in out["controller"]), out.get("controller"))

    def test_event_flag_is_accepted_and_unknown_flag_value_is_usage(self):
        stamp_now(self)
        run("render.py", project=self.dir)
        self.assertEqual(run("check.py", "--event", "stop", project=self.dir).returncode, 0)
        self.assertEqual(run("check.py", "--event", project=self.dir).returncode, 2)


class TestDuplicates(ControllerBase):
    def test_duplicate_release_ids_are_found(self):
        self.d["releases"] = [{"id": "R-01", "name": "a", "stage": "build"},
                              {"id": "R-01 again", "name": "b", "stage": "build"}]
        self.assertEqual(L.duplicate_ids(self.d), ["R-01"])

    def test_two_releases_with_one_id_fail_the_gate(self):
        self.d["releases"] = [{"id": "R-01", "name": "a", "stage": "build"}]
        stamp_now(self)
        self.d["releases"].append({"id": "R-01", "name": "b", "stage": "build"})
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue(any("R-01" in f and "rename the duplicate" in f for f in fails), fails)

    def test_duplicate_task_names_in_one_item_fail_the_gate(self):
        stamp_now(self)
        self.d["plans"]["now"][0]["tasks"].append({"name": "E-01.S2.T1 form", "state": "todo"})
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue(any("E-01.S2.T1 form" in f and "more than once" in f for f in fails), fails)


class TestFixRound1Task2(ControllerBase):
    REMEDY = "revert the hand edit, or run move.py --adopt (with the owner's say-so)"

    def test_release_added_by_hand_fails(self):
        self.d["releases"] = [{"id": "R-01", "name": "R-01 a", "stage": "build"}]
        stamp_now(self)
        self.d["releases"].append({"id": "R-02", "name": "R-02 b", "stage": "production"})
        self.write()
        _, fails, _ = self.gate()
        hit = [f for f in fails if "R-02" in f and "by hand" in f]
        self.assertTrue(hit, fails)
        self.assertIn(self.REMEDY, hit[0])

    def test_release_removed_by_hand_fails(self):
        self.d["releases"] = [{"id": "R-01", "name": "R-01 a", "stage": "build"}]
        stamp_now(self)
        self.d["releases"] = []
        self.write()
        _, fails, _ = self.gate()
        hit = [f for f in fails if "R-01" in f and "by hand" in f]
        self.assertTrue(hit, fails)
        self.assertIn(self.REMEDY, hit[0])

    def test_task_without_state_unchanged_is_clean(self):
        self.d["plans"]["now"][0]["tasks"].append({"name": "E-01.S2.T2 no state"})
        stamp_now(self)
        _, fails, _ = self.gate()
        self.assertEqual(ctl(fails), [], fails)

    def test_item_and_release_with_one_id_are_not_duplicates(self):
        self.d["plans"]["next"].append(item("R-01 cut the release"))
        self.d["releases"] = [{"id": "R-01", "name": "R-01 a", "stage": "build"}]
        self.assertEqual(L.duplicate_ids(self.d), [])

    def test_duplicates_are_reported_even_with_no_stamp(self):
        self.d["plans"]["next"].append(item("E-01.S2 Login page, again"))
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue(any("rename the duplicate" in f for f in fails), fails)
        self.assertTrue(any("move.py --adopt" in f for f in fails), fails)


class TestMove(ControllerBase):
    def setUp(self):
        super().setUp()
        stamp_now(self)

    def test_stage_move_writes_stamps_bumps_and_renders(self):
        r = self.move("E-01.S2", "--stage", "verified", "--status", "suite green")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        d = self.read()
        self.assertEqual(d["plans"]["now"][0]["stage"], "verified")
        self.assertEqual(d["plans"]["now"][0]["status"], "suite green")
        self.assertNotEqual(d["meta"]["updated"], "2026-01-01T00:00:00Z")
        self.assertEqual(self.stamp()["writes"]["items"]["E-01.S2"]["stage"], "verified")
        self.assertIn("building -> verified", r.stdout)
        _, fails, _ = self.gate()
        self.assertEqual(ctl(fails), [], fails)

    def test_task_state_by_task_id_or_full_name(self):
        self.assertEqual(self.move("E-01.S2", "--task", "E-01.S2.T1", "--state", "done").returncode, 0)
        self.assertEqual(self.read()["plans"]["now"][0]["tasks"][0]["state"], "done")
        self.assertEqual(self.move("E-01.S2", "--task", "E-01.S2.T1 form", "--state", "active").returncode, 0)

    def test_to_now_then_done(self):
        self.d = self.read()
        self.d["meta"]["allow_multiple_active"] = True
        self.write()
        L.write_stamp(self.dir, self.d, "test")
        self.assertEqual(self.move("E-01.S3", "--to", "now").returncode, 2, "now needs a status")
        self.assertEqual(self.move("E-01.S3", "--to", "now", "--status", "starting").returncode, 0)
        r = self.move("E-01.S2", "--to", "done", "--outcome", "login works")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("E-01.S2 plans.now -> plans.done", r.stdout)
        d = self.read()
        self.assertEqual([p["name"] for p in d["plans"]["now"]], ["E-01.S3 Logout page"])
        self.assertEqual(d["plans"]["done"][-1]["outcome"], "login works")
        self.assertNotIn("E-01.S2", self.stamp()["writes"]["items"])
        _, fails, _ = self.gate()
        self.assertEqual(ctl(fails), [], fails)

    def test_release_stage(self):
        self.d = self.read()
        self.d["releases"] = [{"id": "R-01", "name": "R-01 Accounts", "stage": "build", "stories": []}]
        self.write()
        L.write_stamp(self.dir, self.d, "test")
        self.assertEqual(self.move("R-01", "--stage", "production").returncode, 0)
        self.assertEqual(self.read()["releases"][0]["stage"], "production")

    def test_refusals_are_exit_2_and_change_nothing(self):
        before = open(os.path.join(self.dir, "plan", "plan.json")).read()
        for args in (("E-09.S1", "--stage", "building"), ("E-01.S2", "--stage", "flying"),
                     ("E-01.S2", "--task", "nope", "--state", "done"),
                     ("E-01.S2", "--task", "E-01.S2.T1", "--state", "finished"),
                     ("E-01.S2", "--to", "done"), ("E-01.S2",), ()):
            r = self.move(*args)
            self.assertEqual(r.returncode, 2, (args, r.stdout + r.stderr))
        self.assertEqual(open(os.path.join(self.dir, "plan", "plan.json")).read(), before)

    def test_adopt_records_what_it_accepted(self):
        self.d = self.read()
        self.d["plans"]["now"][0]["stage"] = "verified"
        self.write()
        r = self.move("--adopt")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("stage of E-01.S2", r.stdout)
        st = self.stamp()
        self.assertEqual(len(st["adopted"]), 1)
        self.assertIn("stage of E-01.S2", st["adopted"][0]["changes"][0])
        _, fails, _ = self.gate()
        self.assertEqual(ctl(fails), [], fails)

    def test_pending_hand_edit_blocks_any_move_and_is_not_adopted(self):
        self.d = self.read()
        self.d["plans"]["now"][0]["stage"] = "verified"
        self.write()
        r = self.move("E-01.S3", "--stage", "grounded")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("pending hand edits", r.stdout)
        self.assertEqual(self.read()["plans"]["next"][0]["stage"], "intent", "nothing written")
        self.assertEqual(self.stamp()["writes"]["items"]["E-01.S2"]["stage"], "building",
                         "the hand edit was not silently adopted")

    def test_release_takes_stage_only(self):
        self.d = self.read()
        self.d["releases"] = [{"id": "R-01", "name": "R-01 Accounts", "stage": "build", "stories": []}]
        self.write()
        L.write_stamp(self.dir, self.d, "test")
        for args in (("--status", "x"), ("--to", "now"), ("--task", "T", "--state", "done")):
            r = self.move("R-01", *args)
            self.assertEqual(r.returncode, 2, (args, r.stdout + r.stderr))
            self.assertIn("releases take --stage only", r.stdout)

    def test_gate_remedy_is_not_a_refused_move(self):
        self.d = self.read()
        self.d["plans"]["now"][0]["stage"] = "verified"
        self.write()
        self.assertEqual(self.move("E-01.S2", "--stage", "verified").returncode, 1,
                         "so the gate's message names revert or --adopt, never this move (N2)")

    def test_duplicate_ids_refusal_says_rename_and_adopt_refuses(self):
        self.d = self.read()
        self.d["plans"]["next"].append(item("E-01.S2 Login page, again"))
        self.write()
        r = self.move("E-01.S3", "--stage", "grounded")
        self.assertEqual(r.returncode, 1)
        self.assertIn("rename", r.stdout)
        self.assertNotIn("run move.py --adopt", r.stdout)
        self.assertEqual(self.move("--adopt").returncode, 1, "adopt cannot clear a duplicate id")

    def test_corrupt_stamp_is_a_message_not_a_traceback(self):
        with open(L.controller_state_path(self.dir), "w") as fh:
            json.dump({"writes": {"items": {"E-01.S2": "not-a-dict"}}}, fh)
        for args in (("E-01.S2", "--stage", "verified"), ("--adopt",)):
            r = self.move(*args)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("stamp unreadable", r.stdout)
            self.assertNotIn("Traceback", r.stderr)

    def test_tracker_reminder_when_a_tracker_is_set(self):
        self.d = self.read()
        self.d["meta"]["tracker"] = {"kind": "notion", "target": "db-1"}
        self.write()
        L.write_stamp(self.dir, self.d, "test")
        r = self.move("E-01.S2", "--stage", "verified")
        self.assertIn("sync.py --tracker", r.stdout)


class TestSoleWriter(unittest.TestCase):
    """The writer matrix is enforced in code: no other script assigns a stamped field."""
    def test_only_move_and_plan_lib_assign_stage_or_state(self):
        import re
        pat = re.compile(r"""\[["'](stage|state)["']\]\s*=(?!=)""")
        for fn in sorted(os.listdir(SCRIPTS)):
            if fn.endswith(".py") and fn not in ("move.py", "plan_lib.py"):
                text = open(os.path.join(SCRIPTS, fn), encoding="utf-8").read()
                self.assertIsNone(pat.search(text), fn)

    def test_only_pause_assigns_meta_paused(self):
        import re
        pat = re.compile(r"""\[["']paused["']\]\s*=(?!=)""")
        for fn in sorted(os.listdir(SCRIPTS)):
            if fn.endswith(".py") and fn != "pause.py":
                self.assertIsNone(pat.search(open(os.path.join(SCRIPTS, fn)).read()), fn)


class TestMoveAdoptDuplicates(ControllerBase):
    def setUp(self):
        super().setUp()
        stamp_now(self)

    def test_adopt_refusal_names_the_duplicate_ids(self):
        self.d["plans"]["next"].append(item("E-01.S2 Login page, again"))
        self.write()
        r = self.move("--adopt")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("E-01.S2", r.stdout)
        self.assertIn("nothing stamped", r.stdout)

    def test_adopt_refusal_names_duplicate_task_names(self):
        self.d["plans"]["now"][0]["tasks"].append({"name": "E-01.S2.T1 form", "state": "todo"})
        self.write()
        r = self.move("--adopt")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("E-01.S2.T1 form", r.stdout)

    def test_first_adopt_with_no_stamp_stamps_and_says_so(self):
        os.remove(L.controller_state_path(self.dir))
        r = self.move("--adopt")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.stamp()["adopted"][0]["changes"], ["first stamp of the current state"])
        _, fails, _ = self.gate()
        self.assertEqual(ctl(fails), [], fails)

    def test_a_release_added_by_hand_is_listed_by_adopt_and_blocks_a_move(self):
        self.d["releases"] = [{"id": "R-05", "name": "R-05 x", "stage": "build", "stories": []}]
        self.write()
        r = self.move("E-01.S2", "--stage", "verified")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("R-05", r.stdout)
        r = self.move("--adopt")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("R-05", r.stdout)


class TestMoveFixRound1(ControllerBase):
    def setUp(self):
        super().setUp()
        stamp_now(self)

    def plan_text(self):
        return open(os.path.join(self.dir, "plan", "plan.json")).read()

    def test_unreadable_stamp_is_exit_2_in_both_paths_for_both_inputs(self):
        for junk in ("{not json", "[]"):
            with open(L.controller_state_path(self.dir), "w") as fh:
                fh.write(junk)
            for args in (("E-01.S2", "--stage", "verified"), ("--adopt",)):
                r = self.move(*args)
                self.assertEqual(r.returncode, 2, (junk, args, r.stdout + r.stderr))
                self.assertIn("stamp unreadable", r.stdout)
                self.assertNotIn("Traceback", r.stderr)
            self.assertEqual(open(L.controller_state_path(self.dir)).read(), junk)

    def test_adopted_not_a_list_is_refused_and_nothing_is_rewritten(self):
        st = self.stamp()
        st["adopted"] = "oops"
        with open(L.controller_state_path(self.dir), "w") as fh:
            json.dump(st, fh)
        before = open(L.controller_state_path(self.dir)).read()
        r = self.move("--adopt")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(open(L.controller_state_path(self.dir)).read(), before)

    def test_adopt_with_controller_off_writes_nothing(self):
        os.remove(L.controller_state_path(self.dir))
        for ctrl in (None, {"one_writer": False}):
            self.d = self.read()
            if ctrl is None:
                self.d["meta"].pop("controller", None)
            else:
                self.d["meta"]["controller"] = ctrl
            self.write()
            r = self.move("--adopt")
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("meta.controller.one_writer is off: nothing to adopt", r.stdout)
            self.assertFalse(os.path.exists(L.controller_state_path(self.dir)))

    def test_same_stage_and_same_bucket_are_no_ops(self):
        before = self.plan_text()
        for args in (("E-01.S2", "--stage", "building"), ("E-01.S2", "--to", "now")):
            r = self.move(*args)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("no change", r.stdout)
            self.assertEqual(self.plan_text(), before)

    def test_to_now_with_another_active_item_is_refused_naming_it(self):
        before = self.plan_text()
        r = self.move("E-01.S3", "--to", "now", "--status", "go")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("E-01.S2", r.stdout)
        self.assertEqual(self.plan_text(), before)

    def test_outcome_without_to_done_is_usage(self):
        r = self.move("E-01.S2", "--stage", "verified", "--outcome", "x")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("--outcome", r.stdout)

    def test_a_render_failure_is_a_warning_not_a_silent_pass(self):
        os.makedirs(os.path.join(self.dir, "plan", "index.html"))
        r = self.move("E-01.S2", "--stage", "verified")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("WARNING: render.py failed", r.stdout)

    def test_move_renders_the_page(self):
        r = self.move("E-01.S2", "--stage", "verified")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        page = open(os.path.join(self.dir, "plan", "index.html"), encoding="utf-8").read()
        self.assertIn("verified", page)

    def test_non_dict_items_and_tasks_are_a_message_not_a_traceback(self):
        self.d = self.read()
        self.d["plans"]["next"].append("junk")
        self.d["plans"]["now"][0]["tasks"].append("junk")
        self.write()
        r = self.move("E-01.S9", "--stage", "building")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        r = self.move("E-01.S2", "--task", "E-01.S2.T1", "--state", "done")
        self.assertNotIn("Traceback", r.stderr)

    def test_read_only_plan_dir_is_a_message(self):
        pdir = os.path.join(self.dir, "plan")
        os.chmod(pdir, 0o500)
        try:
            r = self.move("E-01.S2", "--stage", "verified")
        finally:
            os.chmod(pdir, 0o700)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("cannot write", r.stdout)
        self.assertNotIn("Traceback", r.stderr)


class TestSoleWriterPatterns(unittest.TestCase):
    def test_the_detector_catches_tuple_assignment_and_update(self):
        import re
        pats = [re.compile(p, re.M) for p in (
            r"""\[["'](?:stage|state)["']\]\s*=(?!=)""",
            r"""^\s*[^=\n#]*\[["'](?:stage|state)["']\]\s*,[^=\n]*=(?!=)""",
            r"""^\s*[^=\n#(]*,\s*[\w.\[\]"']+\[["'](?:stage|state)["']\]\s*=(?!=)""",
            r"""\.update\([^)]*["'](?:stage|state)["']\s*:""",
            r"""\.update\([^)]*\b(?:stage|state)\s*=""")]
        for src in ('x["stage"] = 1', 'x["stage"], y = 1, 2', 'y, x["state"] = 1, 2',
                    'it.update({"stage": "a"})', 'it.update(stage="a")'):
            self.assertTrue(any(p.search(src) for p in pats), src)
        for src in ('if x["stage"] == 1:', 'f(x["stage"], y)', 'a = x["stage"]'):
            self.assertFalse(any(p.search(src) for p in pats), src)

    def test_no_other_script_uses_those_forms(self):
        import re
        pats = [re.compile(p, re.M) for p in (
            r"""^\s*[^=\n#]*\[["'](?:stage|state)["']\]\s*,[^=\n]*=(?!=)""",
            r"""^\s*[^=\n#(]*,\s*[\w.\[\]"']+\[["'](?:stage|state)["']\]\s*=(?!=)""",
            r"""\.update\([^)]*["'](?:stage|state)["']\s*:""",
            r"""\.update\([^)]*\b(?:stage|state)\s*=""")]
        for fn in sorted(os.listdir(SCRIPTS)):
            if fn.endswith(".py") and fn not in ("move.py", "plan_lib.py"):
                text = open(os.path.join(SCRIPTS, fn), encoding="utf-8").read()
                for p in pats:
                    self.assertIsNone(p.search(text), (fn, p.pattern))


def stop_hook(project, session=None):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=project)
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "gate_hook.py")], cwd=project, env=env,
                       input=json.dumps({"session_id": session or uuid.uuid4().hex}),
                       capture_output=True, text=True)
    return json.loads(r.stdout) if r.stdout.strip() else {}


class TestTrackerRedGate(ControllerBase):
    def setUp(self):
        super().setUp()
        self.d["meta"]["tracker"] = {"kind": "notion", "target": "db-1"}
        stamp_now(self)

    def test_without_controller_tracker_signals_stay_drift(self):
        del self.d["meta"]["controller"]
        self.write()
        _, fails, drifts = self.gate()
        self.assertFalse([f for f in fails if "tracker mirror" in f], fails)
        self.assertTrue([m for m in drifts if "never reconciled" in m], drifts)

    def test_with_controller_never_reconciled_fails(self):
        _, fails, _ = self.gate()
        self.assertTrue([f for f in fails if "never reconciled" in f], fails)

    def test_stop_hook_blocks_with_the_reconcile_step(self):
        run("render.py", project=self.dir)
        out = stop_hook(self.dir)
        self.assertEqual(out.get("decision"), "block", out)
        self.assertIn("tracker.py diff --actual", out["reason"])

    def test_reconciled_clean_then_a_move_reddens_it_again(self):
        exp = json.loads(run("tracker.py", "expected", project=self.dir).stdout)["rows"]
        p = os.path.join(self.dir, "actual.json")
        json.dump([{k: v for k, v in r.items() if k != "key"} for r in exp], open(p, "w"))
        self.assertEqual(run("tracker.py", "diff", "--actual", p, project=self.dir).returncode, 0)
        _, fails, _ = self.gate()
        self.assertFalse([f for f in fails if "tracker mirror" in f], fails)
        self.assertEqual(self.move("E-01.S2", "--stage", "verified").returncode, 0)
        _, fails, _ = self.gate()
        self.assertTrue([f for f in fails if "tracker mirror" in f and "differ" in f], fails)

    def test_stop_hook_silent_on_the_same_failure_set(self):
        run("render.py", project=self.dir)
        sid = uuid.uuid4().hex
        self.assertEqual(stop_hook(self.dir, sid).get("decision"), "block")
        self.assertEqual(stop_hook(self.dir, sid), {})

    def test_controller_crash_is_a_fail(self):
        import check
        import controller
        run("render.py", project=self.dir)
        real = controller.findings
        controller.findings = lambda *a, **k: 1 / 0
        try:
            fails, _, _ = check.run(self.dir)
        finally:
            controller.findings = real
        self.assertTrue([m for _, m in fails if "check crashed" in m], fails)

    def test_relational_fault_is_a_gate_fail(self):
        self.d["meta"]["tracker"]["relational"] = True
        self.d["epics"] = []
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in fails if "not declared in epics" in f], fails)

    def test_tracker_message_text_is_unchanged_from_0_18(self):
        del self.d["meta"]["controller"]
        self.write()
        _, _, drifts = self.gate()
        self.assertIn("tracker mirror (notion) was never reconciled — fetch its rows and run "
                      "tracker.py diff --actual <file>", drifts)

    def test_callers_pass_their_event(self):
        self.d["meta"]["controller"]["base"] = "no-such-branch"  # a bound rule then reports its event
        self.d["meta"]["controller"]["rules"] = [
            dict(RULE, name="r-%s" % e, on=[e]) for e in ("stop", "session-start", "sync", "pause")]
        self.d["meta"]["tracker"] = {"kind": "notion", "target": "db-1"}
        stamp_now(self)
        run("render.py", project=self.dir)
        self.assertIn("on stop:", stop_hook(self.dir)["reason"])
        r = run("brief.py", "--session-start", project=self.dir)
        self.assertIn("on session-start:", r.stdout)
        r = run("sync.py", project=self.dir)
        self.assertIn("on sync:", r.stdout)
        self.assertNotIn("on session-start:", r.stdout)
        run("pause.py", project=self.dir)
        handoff = open(os.path.join(self.dir, "plan", "HANDOFF.md")).read()
        self.assertIn("on pause:", handoff)

    def test_unknown_or_empty_event_is_a_usage_error(self):
        for ev in ("lunch", "", "stage:", "release:"):
            r = run("check.py", "--event", ev, project=self.dir)
            self.assertEqual(r.returncode, 2, (ev, r.stdout))
            self.assertIn("usage", r.stdout)
        self.assertEqual(run("check.py", "--event", "stage:verified", project=self.dir).returncode in (0, 1), True)

    def test_paused_fail_comes_after_controller_fails(self):
        self.d["meta"]["paused"] = "bad"
        self.d["meta"]["controller"]["one_writer"] = True
        self.d["plans"]["now"][0]["stage"] = "verified"
        self.write()
        _, fails, _ = self.gate()
        i = [n for n, f in enumerate(fails) if "meta.paused" in f]
        j = [n for n, f in enumerate(fails) if "by hand" in f]
        self.assertTrue(i and j, fails)
        self.assertGreater(i[0], j[0])

    def test_relational_drift_lines_are_capped(self):
        del self.d["meta"]["controller"]
        self.d["meta"]["tracker"]["relational"] = True
        self.d["epics"] = []
        self.d["plans"]["next"] = [item("E-02.S%d x" % n) for n in range(15)]
        self.write()
        _, _, drifts = self.gate()
        rel = [m for m in drifts if "not declared in epics" in m or "more" in m]
        self.assertLessEqual(len(rel), 11, rel)
        self.assertTrue([m for m in drifts if "… and " in m and "more" in m], drifts)


def git(cwd, *a):
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t"] + list(a),
                   cwd=cwd, check=True, capture_output=True)


RULE = {"name": "changelog with code", "on": ["stage:verified"], "if_changed": ["src/*.py"],
        "then_changed": ["CHANGELOG.md"], "why": "a missed changelog entry was caught by hand twice"}


class TestRules(ControllerBase):
    def setUp(self):
        super().setUp()
        self.d["meta"]["controller"]["rules"] = [dict(RULE)]
        git(self.dir, "checkout", "-q", "-b", "main")
        os.makedirs(os.path.join(self.dir, "src"))
        open(os.path.join(self.dir, "src", "app.py"), "w").write("x = 1\n")
        open(os.path.join(self.dir, "CHANGELOG.md"), "w").write("# log\n")
        stamp_now(self)
        run("render.py", project=self.dir)
        git(self.dir, "add", "-A")
        git(self.dir, "commit", "-q", "-m", "base")
        git(self.dir, "checkout", "-q", "-b", "feature")
        open(os.path.join(self.dir, "src", "app.py"), "a").write("y = 2\n")

    def test_rule_fires_only_on_its_event(self):
        _, fails, _ = self.gate()
        self.assertFalse([f for f in fails if "changelog with code" in f], fails)
        r = run("check.py", "--json", "--event", "stage:verified", project=self.dir)
        out = json.loads(r.stdout)
        hit = [f for f in out["fails"] if "changelog with code" in f]
        self.assertTrue(hit, out["fails"])
        self.assertIn("CHANGELOG.md", hit[0])
        self.assertIn("src/app.py", hit[0])

    def test_failing_rule_refuses_the_move_and_writes_nothing(self):
        before = open(os.path.join(self.dir, "plan", "plan.json")).read()
        r = self.move("E-01.S2", "--stage", "verified")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("changelog with code", r.stdout)
        self.assertEqual(open(os.path.join(self.dir, "plan", "plan.json")).read(), before)

    def test_satisfied_rule_lets_the_move_through(self):
        open(os.path.join(self.dir, "CHANGELOG.md"), "a").write("- y\n")
        self.assertEqual(self.move("E-01.S2", "--stage", "verified").returncode, 0)

    def test_unmeasurable_base_fails_loudly_never_passes(self):
        self.d = self.read()
        self.d["meta"]["controller"]["base"] = "no-such-branch"
        self.write()
        L.write_stamp(self.dir, self.d, "test")
        r = self.move("E-01.S2", "--stage", "verified")
        self.assertEqual(r.returncode, 1)
        self.assertIn("cannot measure", r.stdout)

    def test_on_the_base_branch_itself_measures_nothing_and_fails(self):
        git(self.dir, "checkout", "-q", "main")
        r = self.move("E-01.S2", "--stage", "verified")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("base branch", r.stdout)

    def test_fresh_branch_with_no_commit_is_measured_from_the_working_tree(self):
        # setUp's feature branch has no commit of its own: merge-base == HEAD.
        open(os.path.join(self.dir, "CHANGELOG.md"), "a").write("- y\n")
        r = self.move("E-01.S2", "--stage", "verified")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_committed_change_on_the_branch_counts_too(self):
        git(self.dir, "commit", "-q", "-am", "feature work")
        r = self.move("E-01.S2", "--stage", "verified")
        self.assertEqual(r.returncode, 1, "src/app.py committed, CHANGELOG untouched")

    def test_adopt_runs_the_rules_of_each_stage_it_accepts(self):
        self.d = self.read()
        self.d["plans"]["now"][0]["stage"] = "verified"
        self.write()
        before = self.stamp()
        r = self.move("--adopt")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("changelog with code", r.stdout)
        self.assertEqual(self.stamp(), before, "a refused adopt stamps nothing")
        open(os.path.join(self.dir, "CHANGELOG.md"), "a").write("- y\n")
        self.assertEqual(self.move("--adopt").returncode, 0)

    def test_first_opt_in_adopt_does_not_fire_rules(self):
        os.remove(L.controller_state_path(self.dir))
        self.d = self.read()
        self.d["plans"]["now"][0]["stage"] = "verified"
        self.write()
        r = self.move("--adopt")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("first opt-in", r.stdout)

    def test_rule_shape_faults(self):
        import controller
        stages = ["intent", "verified"]
        self.assertEqual(controller.rule_faults([dict(RULE)], stages), [])
        for bad, word in (({"on": ["lunch"]}, "lunch"), ({"on": ["stage:flying"]}, "flying"),
                          ({"why": ""}, "why"), ({"then_changed": []}, "then_changed"),
                          ({"extra": 1}, "extra")):
            rule = dict(RULE, **bad)
            faults = controller.rule_faults([rule], stages)
            self.assertTrue(any(word in f for f in faults), (bad, faults))

    def test_bad_rule_is_a_gate_fail_on_any_event(self):
        self.d = self.read()
        self.d["meta"]["controller"]["rules"] = [dict(RULE, on=["lunch"])]
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in fails if "lunch" in f], fails)

    def test_release_event(self):
        self.d = self.read()
        self.d["releases"] = [{"id": "R-01", "name": "R-01 x", "stage": "build", "stories": []}]
        self.d["meta"]["controller"]["rules"] = [dict(RULE, on=["release:production"])]
        self.write()
        L.write_stamp(self.dir, self.d, "test")
        self.assertEqual(self.move("R-01", "--stage", "production").returncode, 1)
        self.assertEqual(self.move("R-01", "--stage", "gate").returncode, 0)


class TestRulesFixRound1(ControllerBase):
    """Silent passes: subdirectory project, non-ASCII path, full-ref base, git failure; soft base-branch case."""

    V = ("E-01.S2", "--stage", "verified")

    def build(self, sub=None, base=None, branch=True):
        root = self.dir
        proj = os.path.join(root, sub) if sub else root
        self.d["meta"]["controller"]["rules"] = [dict(RULE)]
        if base:
            self.d["meta"]["controller"]["base"] = base
        git(root, "checkout", "-q", "-b", "main")
        os.makedirs(os.path.join(proj, "src"))
        os.makedirs(os.path.join(proj, "plan"), exist_ok=True)
        open(os.path.join(proj, "src", "app.py"), "w").write("x = 1\n")
        open(os.path.join(proj, "CHANGELOG.md"), "w").write("# log\n")
        self.dir = proj
        stamp_now(self)
        run("render.py", project=proj)
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "base")
        if branch:
            git(root, "checkout", "-q", "-b", "feature")
        return root, proj

    def test_subdirectory_project_committed_change_is_seen(self):
        root, proj = self.build(sub="svc")
        open(os.path.join(proj, "src", "app.py"), "a").write("y = 2\n")
        git(root, "commit", "-q", "-am", "work")
        self.assertEqual(self.move(*self.V).returncode, 1)

    def test_subdirectory_project_untracked_change_is_seen(self):
        root, proj = self.build(sub="svc")
        open(os.path.join(proj, "src", "new.py"), "w").write("z = 1\n")
        self.assertEqual(self.move(*self.V).returncode, 1)
        open(os.path.join(proj, "CHANGELOG.md"), "a").write("- z\n")
        self.assertEqual(self.move(*self.V).returncode, 0)

    def test_non_ascii_path_is_matched(self):
        root, proj = self.build()
        open(os.path.join(proj, "src", "café.py"), "w").write("c = 1\n")
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "cafe")
        self.assertEqual(self.move(*self.V).returncode, 1)

    def test_base_spelled_as_a_full_ref_is_still_the_base(self):
        root, proj = self.build(base="refs/heads/main", branch=False)
        open(os.path.join(proj, "src", "app.py"), "a").write("y = 2\n")
        git(root, "commit", "-q", "-am", "on main")
        r = self.move(*self.V)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("base branch", r.stdout)

    def test_on_base_session_events_are_drift_not_fail(self):
        root, proj = self.build(branch=False)
        self.d = self.read()
        self.d["meta"]["controller"]["rules"] = [dict(RULE, on=["stop"])]
        self.write()
        L.write_stamp(self.dir, self.d, "test")
        r = run("check.py", "--json", "--event", "stop", project=proj)
        out = json.loads(r.stdout)
        self.assertFalse([f for f in out["fails"] if "changelog with code" in f], out["fails"])
        self.assertTrue([m for m in out["drifts"] if "measured nothing: HEAD is the base branch" in m],
                        out["drifts"])
        import gate_hook
        self.assertTrue(any(k in "measured nothing: HEAD is the base branch" for k in gate_hook.WORK_IN_PROGRESS))

    def test_on_base_stage_event_still_refuses(self):
        self.build(branch=False)
        self.assertEqual(self.move(*self.V).returncode, 1)

    def test_missing_base_is_fail_even_for_a_session_event(self):
        self.build()
        self.d = self.read()
        self.d["meta"]["controller"].update(base="no-such-branch", rules=[dict(RULE, on=["stop"])])
        self.write()
        L.write_stamp(self.dir, self.d, "test")
        out = json.loads(run("check.py", "--json", "--event", "stop", project=self.dir).stdout)
        self.assertTrue([f for f in out["fails"] if "cannot measure" in f], out["fails"])

    def test_git_diff_failure_is_unmeasurable_not_empty(self):
        import controller
        self.build()
        real = controller._git_ok
        controller._git_ok = lambda root, *a: None if "diff" in a else real(root, *a)
        try:
            files, why = controller.changed_files(self.dir, "main")
        finally:
            controller._git_ok = real
        self.assertIsNone(files)
        self.assertIn("cannot measure", why)

    def test_malformed_rules_refuse_the_move_cleanly(self):
        root, proj = self.build()
        for bad in ({"then_changed": "CHANGELOG.md"}, {"on": ["stage:verified", "lunch"]}):
            self.d = self.read()
            self.d["meta"]["controller"]["rules"] = [dict(RULE, **bad)]
            self.write()
            L.write_stamp(self.dir, self.d, "test")
            before = open(os.path.join(self.dir, "plan", "plan.json")).read()
            r = self.move(*self.V)
            self.assertEqual(r.returncode, 1, (bad, r.stdout, r.stderr))
            self.assertNotIn("Traceback", r.stderr)
            self.assertIn("then_changed" if "then_changed" in bad else "lunch", r.stdout)
            self.assertEqual(open(os.path.join(self.dir, "plan", "plan.json")).read(), before)

    def test_adopt_refuses_on_malformed_rules(self):
        self.build()
        self.d = self.read()
        self.d["meta"]["controller"]["rules"] = [dict(RULE, then_changed="CHANGELOG.md")]
        self.d["plans"]["now"][0]["stage"] = "verified"
        self.write()
        r = self.move("--adopt")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_event_with_unknown_stage_is_a_usage_error(self):
        self.build()
        r = run("check.py", "--event", "stage:bogus", project=self.dir)
        self.assertEqual(r.returncode, 2, r.stdout)


class TestDocs(unittest.TestCase):
    def test_skill_writer_table_equals_the_code(self):
        import re
        text = open(os.path.join(PLUGIN, "skills", "plan-layer", "SKILL.md"), encoding="utf-8").read()
        block = re.search(r"<!-- writer-matrix -->(.*?)<!-- /writer-matrix -->", text, re.S)
        self.assertTrue(block, "SKILL.md has no writer-matrix block")
        rows = [[c.strip().strip("`") for c in ln.strip().strip("|").split("|")]
                for ln in block.group(1).splitlines()
                if ln.startswith("|") and not re.match(r"^\|\s*(Field|-)", ln)]
        self.assertEqual(rows, [[w["field"], w["writer"], w["enforced"]] for w in L.WRITERS])

    def test_version_is_0_19_0_with_a_changelog_entry(self):
        with open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json")) as fh:
            pl = json.load(fh)
        self.assertEqual(pl["version"], "0.19.0")
        with open(os.path.join(PLUGIN, "CHANGELOG.md"), encoding="utf-8") as fh:
            self.assertTrue(fh.read().startswith("# Changelog\n\n## 0.19.0"))

    def test_no_private_names_in_the_new_files(self):
        """Generic examples only; the scan list itself is kept outside the repo."""
        for rel in ("scripts/controller.py", "scripts/move.py", "tests/test_controller.py",
                    "tests/test_relational.py", "tests/test_inventory.py"):
            with open(os.path.join(PLUGIN, rel), encoding="utf-8") as fh:
                text = fh.read()
            self.assertNotRegex(text, r"https?://(www\.)?notion\.so/", rel)
