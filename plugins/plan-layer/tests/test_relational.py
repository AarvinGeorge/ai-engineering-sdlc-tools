"""Relational tracker reconcile (0.19.0): epics, stories, tasks and releases with
their links, opt-in through meta.tracker.relational. Flat mode is unchanged."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_light_and_budget import Base, run  # noqa: E402
from test_tracker import TrackerBase, item  # noqa: E402
import plan_lib as L  # noqa: E402
import tracker  # noqa: E402

# Captured from the untouched 0.18.0 code (literal, never recomputed).
FLAT_GOLDEN = json.loads(r"""{
 "rows": [
  {
   "key": "E-01.S2",
   "Name": "E-01.S2 Login page",
   "Status": "In progress",
   "Stage": "building",
   "Updated": "2026-01-01T00:00:00Z",
   "Link": "docs/p.md"
  },
  {
   "key": "E-01.S3",
   "Name": "E-01.S3 Logout page",
   "Status": "Idea",
   "Stage": "intent",
   "Updated": "2026-01-01T00:00:00Z"
  }
 ],
 "hash": "f6a176537787ee30"
}""")


class RelBase(TrackerBase):
    def setUp(self):
        super().setUp()
        self.d["meta"]["naming"] = "work-ids"
        self.d["meta"]["tracker"]["relational"] = True
        self.d["plans"]["now"][0]["tasks"] = [{"name": "E-01.S2.T1 form", "state": "active"},
                                              {"name": "untracked step", "state": "todo"}]
        self.d["epics"] = [{"id": "E-01", "name": "E-01 Accounts"}]
        self.d["releases"] = [{"id": "R-01", "name": "R-01 Accounts", "stage": "build",
                               "stories": ["E-01.S2"]}]

    def rows(self):
        self.write()
        d = L.load(self.dir)
        cfg, err = L.tracker_config(d, self.dir)
        self.assertIsNone(err)
        return {r["key"]: r for r in tracker.expected_rows(d, cfg)}


class TestFlatUnchanged(TrackerBase):
    def test_flat_rows_and_hash_byte_identical_to_0_18(self):
        self.write()
        d = L.load(self.dir)
        cfg, _ = L.tracker_config(d, self.dir)
        rows = tracker.expected_rows(d, cfg)
        self.assertEqual({"rows": rows, "hash": tracker.expected_hash(rows, cfg)}, FLAT_GOLDEN)


class TestRelationalRows(RelBase):
    def test_every_kind_with_its_links(self):
        r = self.rows()
        self.assertEqual(r["E-01"]["kind"], "epic")
        self.assertEqual(r["E-01"]["Name"], "E-01 Accounts")
        self.assertEqual(r["E-01"]["Status"], "In progress", "an epic with a story in now is building")
        self.assertEqual(r["E-01.S2"]["kind"], "story")
        self.assertEqual(r["E-01.S2"]["Epic"], "E-01 Accounts")
        self.assertEqual(r["E-01.S2"]["Release"], "R-01 Accounts")
        self.assertNotIn("Release", r["E-01.S3"])
        self.assertEqual(r["E-01.S2.T1"]["kind"], "task")
        self.assertEqual(r["E-01.S2.T1"]["Story"], "E-01.S2 Login page")
        self.assertEqual(r["E-01.S2.T1"]["Status"], "In progress")
        self.assertEqual(r["R-01"]["kind"], "release")
        self.assertEqual(r["R-01"]["Status"], "build", "no release_status_map: the stage as is")

    def test_task_without_a_task_id_is_not_mirrored_and_expected_says_so(self):
        self.write()
        out = run("tracker.py", "expected", project=self.dir)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        body = json.loads(out.stdout)
        self.assertNotIn("untracked step", json.dumps(body["rows"]))
        self.assertEqual(body["not_mirrored"], ["E-01.S2: untracked step"])

    def test_epic_status_done_when_every_story_is_finished(self):
        self.d["plans"]["now"], self.d["plans"]["next"] = [], []
        self.d["plans"]["done"] = [{"name": "E-01.S1 Signup", "period": "p", "outcome": "o"}]
        self.d["releases"][0]["stories"] = []
        self.assertEqual(self.rows()["E-01"]["Status"], "Done")

    def test_relational_hash_changes_with_a_link(self):
        self.write()
        d = L.load(self.dir)
        cfg, _ = L.tracker_config(d, self.dir)
        h1 = tracker.expected_hash(tracker.expected_rows(d, cfg), cfg)
        d["releases"][0]["stories"] = []
        self.assertNotEqual(h1, tracker.expected_hash(tracker.expected_rows(d, cfg), cfg))


class TestRelationalFaults(RelBase):
    def test_faults(self):
        cases = [
            (lambda d: d["meta"].pop("naming"), "work-ids"),
            (lambda d: d.__setitem__("epics", []), "E-01"),
            (lambda d: d["releases"].append({"id": "R-02", "name": "R-02 x", "stage": "build",
                                             "stories": ["E-01.S2"]}), "two releases"),
            (lambda d: d["plans"]["now"][0]["tasks"].append({"name": "E-01.S3.T1 x", "state": "todo"}),
             "E-01.S3.T1"),
        ]
        for mutate, word in cases:
            self.setUp()
            mutate(self.d)
            faults = tracker.relational_faults(self.d)
            self.assertTrue(any(word in f for f in faults), (word, faults))


if __name__ == "__main__":
    unittest.main()
