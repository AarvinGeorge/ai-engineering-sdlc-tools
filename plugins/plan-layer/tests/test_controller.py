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
