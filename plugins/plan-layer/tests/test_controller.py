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
        self.assertTrue(any("controller crashed" in f for f in fails), fails)

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
