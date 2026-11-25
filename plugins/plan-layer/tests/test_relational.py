"""Relational tracker reconcile (0.19.0): epics, stories, tasks and releases with
their links, opt-in through meta.tracker.relational. Flat mode is unchanged."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_light_and_budget import run  # noqa: E402
from test_tracker import TrackerBase  # noqa: E402
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
        return {r["key"]: r for r in tracker.expected_rows(d, cfg, self.dir)}


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
            with self.subTest(word=word):
                self.setUp()
                self.addCleanup(self.tearDown)
                mutate(self.d)
                faults = tracker.relational_faults(self.d)
                self.assertTrue(any(word in f for f in faults), (word, faults))

    def faults_after(self, mutate):
        mutate(self.d)
        return tracker.relational_faults(self.d)

    def test_task_named_with_the_story_id_is_a_fault_not_a_duplicate_key(self):
        def m(d):
            d["plans"]["now"][0]["tasks"].append({"name": "E-01.S2 polish", "state": "todo"})
        self.assertTrue(any("E-01.S2" in f and "task" in f for f in self.faults_after(m)))
        cfg = self.cfg()
        keys = [r["key"] for r in tracker.expected_rows(self.d, cfg, self.dir)]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn("E-01.S2: E-01.S2 polish", tracker.not_mirrored(self.d))

    def cfg(self):
        self.write()
        return L.tracker_config(L.load(self.dir), self.dir)[0]

    def test_wrong_story_and_finding_tasks_are_listed_not_mirrored(self):
        def m(d):
            d["plans"]["now"][0]["tasks"] += [{"name": "E-01.S3.T1 x", "state": "todo"},
                                              {"name": "E-01.F1 odd", "state": "todo"}]
        self.faults_after(m)
        nm = tracker.not_mirrored(self.d)
        self.assertIn("E-01.S2: E-01.S3.T1 x", nm)
        self.assertIn("E-01.S2: E-01.F1 odd", nm)
        self.assertNotIn("E-01.S2: E-01.S2.T1 form", nm)

    def test_item_with_a_declared_epic_id_is_a_fault(self):
        def m(d):
            d["plans"]["next"].append({"name": "E-01 Whole epic", "why": "w", "unblocks": "u",
                                       "stage": "intent", "plan_file": None})
        self.assertTrue(any("E-01" in f and "epic" in f for f in self.faults_after(m)))

    def test_release_listing_an_unknown_story_is_a_fault(self):
        def m(d):
            d["releases"][0]["stories"] = ["E-01.S9"]
        self.assertTrue(any("E-01.S9" in f for f in self.faults_after(m)))

    def test_malformed_epics_and_releases_are_skipped_and_reported(self):
        def m(d):
            d["epics"] += ["E-02", {"id": "E-03"}]
            d["releases"] += [{"id": "R-02", "name": "R-02 x"}, "R-03"]
        faults = self.faults_after(m)
        self.assertTrue(any("epics[1]" in f for f in faults), faults)
        self.assertTrue(any("epics[2]" in f for f in faults), faults)
        self.assertTrue(any("releases[1]" in f for f in faults), faults)
        self.assertTrue(any("releases[2]" in f for f in faults), faults)
        self.write()
        d = L.load(self.dir)
        cfg, _ = L.tracker_config(d, self.dir)
        keys = {r["key"] for r in tracker.expected_rows(d, cfg, self.dir)}
        self.assertEqual({k for k in keys if k[0] in "ER" and "." not in k}, {"E-01", "R-01"})


class TestEpicStatusFromAllFinishedWork(RelBase):
    def done_items(self, n, epic="E-02"):
        return [{"name": "%s.S%d old" % (epic, i), "period": "p", "outcome": "o"}
                for i in range(1, n + 1)]

    def test_finished_epic_outside_the_recent_done_window_is_done(self):
        self.d["epics"].append({"id": "E-02", "name": "E-02 Billing"})
        self.d["meta"]["tracker"]["recent_done"] = 0
        self.d["plans"]["done"] = self.done_items(7)
        self.assertEqual(self.rows()["E-02"]["Status"], "Done")

    def test_finished_epic_whose_stories_are_only_in_the_archive_is_done(self):
        self.d["epics"].append({"id": "E-02", "name": "E-02 Billing"})
        self.write()
        os.makedirs(os.path.join(self.dir, "plan", "archive"), exist_ok=True)
        with open(os.path.join(self.dir, "plan", "archive", "done.json"), "w") as fh:
            json.dump(self.done_items(2), fh)
        d = L.load(self.dir)
        cfg, _ = L.tracker_config(d, self.dir)
        r = {x["key"]: x for x in tracker.expected_rows(d, cfg, self.dir)}
        self.assertEqual(r["E-02"]["Status"], "Done")


class TestConfigFetch(RelBase):
    def test_relational_adapter_without_a_fetch_instruction_gives_empty_fetch(self):
        os.makedirs(os.path.join(self.dir, "plan", "trackers"), exist_ok=True)
        with open(os.path.join(self.dir, "plan", "trackers", "notion.json"), "w") as fh:
            json.dump({"kind": "notion", "fields": {"name": "Name", "status": "Status"},
                       "status_map": {"paused": "Paused", "done": "Done"},
                       "relations": {"epic": "Epic", "story": "Story", "release": "Release"}}, fh)
        self.write()
        cfg, err = L.tracker_config(L.load(self.dir), self.dir)
        self.assertIsNone(err)
        self.assertEqual(cfg["fetch"], "")


class TestRelationalDiff(RelBase):
    def good(self):
        self.write()
        body = json.loads(run("tracker.py", "expected", project=self.dir).stdout)
        return [dict(r) for r in body["rows"]]

    def diff(self, rows):
        p = self.actual_file([{k: v for k, v in r.items() if k != "key"} for r in rows])
        return self.tracker("diff", "--actual", p)

    def test_clean_and_records_actual_keys(self):
        r = self.diff(self.good())
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("E-01.S2.T1", self.state()["actual_keys"])

    def test_missing_task_row_is_created_with_its_story_link(self):
        rows = [r for r in self.good() if r["key"] != "E-01.S2.T1"]
        r = self.diff(rows)
        self.assertEqual(r.returncode, 1)
        self.assertIn("create task row", r.stdout)
        self.assertIn("Story='E-01.S2 Login page'", r.stdout)

    def test_wrong_link_is_a_set_instruction(self):
        rows = self.good()
        for row in rows:
            if row["key"] == "E-01.S3":
                row["Release"] = "R-01 Accounts"
        r = self.diff(rows)
        self.assertEqual(r.returncode, 1)
        self.assertIn("set Release of 'E-01.S3 Logout page' to ''", r.stdout)

    def test_link_compared_on_work_id_so_a_retitled_epic_still_matches(self):
        rows = self.good()
        for row in rows:
            if row["key"] == "E-01.S2":
                row["Epic"] = "E-01 Accounts and sessions"
        self.assertEqual(self.diff(rows).returncode, 0)

    def test_same_id_under_another_kind_is_not_a_match(self):
        rows = self.good()
        for row in rows:
            if row["key"] == "R-01":
                row["kind"] = "story"
        r = self.diff(rows)
        self.assertEqual(r.returncode, 1)
        self.assertIn("create release row", r.stdout)

    def test_row_without_kind_is_unreadable_exit_2(self):
        rows = self.good()
        rows[0].pop("kind")
        r = self.diff(rows)
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("kind", r.stdout)

    def test_stray_epic_is_flagged(self):
        rows = self.good() + [{"kind": "epic", "Name": "E-07 Billing", "Status": "Planned"}]
        r = self.diff(rows)
        self.assertIn("row 'E-07 Billing' not in the plan", r.stdout)

    def test_plan_fault_exits_2_before_comparing(self):
        self.d["epics"] = []
        self.write()
        r = self.tracker("diff", "--actual", self.actual_file([]))
        self.assertEqual(r.returncode, 2)
        self.assertIn("not declared in epics", r.stdout)
        self.assertIsNone(self.state())


if __name__ == "__main__":
    unittest.main()
