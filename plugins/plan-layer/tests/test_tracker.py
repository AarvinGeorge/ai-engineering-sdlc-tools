"""External-tracker mirror: meta.tracker, trackers/<kind>.json adapters,
scripts/tracker.py expected|diff, sync.py --tracker, and the gate's signals.
Absent meta.tracker means the feature is off and every plan is unchanged."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_light_and_budget import Base, PLUGIN, run  # noqa: E402

TRACKERS = os.path.join(PLUGIN, "trackers")


def item(name, stage="intent", **kw):
    d = {"name": name, "why": "w", "unblocks": "u", "stage": stage, "plan_file": None}
    d.update(kw)
    return d


def tracker_msgs(msgs):
    return [m for m in msgs if "tracker" in m.lower()]


class TrackerBase(Base):
    def setUp(self):
        super().setUp()
        self.d["meta"]["tracker"] = {"kind": "notion", "target": "db-123"}
        self.d["plans"]["now"] = [item("E-01.S2 Login page", "building", plan_file="docs/p.md",
                                       status="s", updated="2026-01-01",
                                       tasks=[{"name": "t", "state": "todo"}])]
        self.d["plans"]["next"] = [item("E-01.S3 Logout page")]
        self.d["plans"]["done"] = []

    def tracker(self, *args):
        return run("tracker.py", *args, project=self.dir)

    def actual_file(self, rows, name="actual.json", raw=None):
        p = os.path.join(self.dir, name)
        with open(p, "w") as fh:
            fh.write(raw if raw is not None else json.dumps(rows))
        return p

    def expected(self):
        r = self.tracker("expected")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(r.stdout)

    def state(self):
        p = os.path.join(self.dir, "plan", "tracker-state.json")
        return json.load(open(p)) if os.path.isfile(p) else None


class TestAdapters(unittest.TestCase):
    def test_adapter_files_have_the_required_shape(self):
        for kind in ("notion", "generic"):
            a = json.load(open(os.path.join(TRACKERS, kind + ".json"), encoding="utf-8"))
            for f in ("name", "status", "stage", "updated", "link"):
                self.assertIn(f, a["fields"], (kind, f))
            for s in ("intent", "grounded", "planned", "building", "verified", "recorded",
                      "paused", "done"):
                self.assertTrue(a["status_map"].get(s), (kind, s))
            self.assertTrue(a.get("fetch"), kind)

    def test_readme_explains_adding_an_adapter(self):
        text = open(os.path.join(TRACKERS, "README.md")).read()
        for word in ("fields", "status_map", "fetch"):
            self.assertIn(word, text)


class TestFeatureOff(Base):
    def test_absent_tracker_changes_nothing(self):
        self.d["plans"]["next"] = [item("First thing")]
        self.write()
        _, fails, drifts = self.gate()
        self.assertEqual(tracker_msgs(fails + drifts), [], fails + drifts)

    def test_tracker_commands_refuse_loudly_when_off(self):
        self.write()
        r = run("tracker.py", "expected", project=self.dir)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("meta.tracker", r.stdout + r.stderr)

    def test_sync_without_flag_does_not_touch_tracker(self):
        self.d["meta"]["tracker"] = {"kind": "notion", "target": "x"}
        self.write()
        r = run("sync.py", project=self.dir)
        self.assertNotIn("sync: tracker", r.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "plan", "tracker-state.json")))


class TestExpected(TrackerBase):
    def test_rows_for_now_next_and_recent_done(self):
        self.d["plans"]["done"] = [{"name": "E-00.S%d Old %d" % (i, i), "period": "p", "outcome": "o"}
                                   for i in range(8)]
        self.write()
        out = self.expected()
        rows = out["rows"]
        names = [r["Name"] for r in rows]
        self.assertEqual(names[:2], ["E-01.S2 Login page", "E-01.S3 Logout page"])
        done = [r for r in rows if r["Status"] == "Done"]
        self.assertEqual(len(done), 5, "recent done is the last five, not all eight")
        self.assertEqual([r["Name"] for r in done][-1], "E-00.S7 Old 7")
        self.assertNotIn("E-00.S0 Old 0", names)
        first = rows[0]
        self.assertEqual(first["key"], "E-01.S2")
        self.assertEqual(first["Stage"], "building")
        self.assertEqual(first["Updated"], "2026-01-01T00:00:00Z")
        self.assertEqual(first["Status"], json.load(open(os.path.join(TRACKERS, "notion.json")))["status_map"]["building"])

    def test_key_falls_back_to_name_without_a_work_id(self):
        self.d["plans"]["next"] = [item("Tidy the docs")]
        self.write()
        rows = self.expected()["rows"]
        self.assertEqual(rows[-1]["key"], "Tidy the docs")

    def test_paused_makes_active_items_paused_not_next(self):
        self.d["meta"]["paused"] = {"at": "2026-01-01T00:00:00Z"}
        self.write()
        rows = {r["key"]: r for r in self.expected()["rows"]}
        self.assertEqual(rows["E-01.S2"]["Status"], "Paused")
        self.assertNotEqual(rows["E-01.S3"]["Status"], "Paused")

    def test_overrides_apply(self):
        self.d["meta"]["tracker"].update({"status_map": {"building": "Doing"},
                                          "fields": {"status": "State"}, "recent_done": 1})
        self.d["plans"]["done"] = [{"name": "E-00 a", "period": "p", "outcome": "o"},
                                   {"name": "E-00.S1 b", "period": "p", "outcome": "o"}]
        self.write()
        rows = self.expected()["rows"]
        self.assertEqual(rows[0]["State"], "Doing")
        self.assertEqual(len([r for r in rows if r["State"] == "Done"]), 1)

    def test_link_present_only_when_there_is_one(self):
        self.write()
        rows = self.expected()["rows"]
        self.assertEqual(rows[0]["Link"], "docs/p.md")
        self.assertNotIn("Link", rows[1])


class TestDiff(TrackerBase):
    def good_rows(self):
        return [{"Name": r["Name"], "Status": r["Status"], "Stage": r["Stage"]}
                for r in self.expected()["rows"]]

    def test_clean_exits_0_and_records_the_reconcile(self):
        self.write()
        r = self.tracker("diff", "--actual", self.actual_file(self.good_rows()))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        st = self.state()
        self.assertEqual(st["drift"], 0)
        self.assertEqual(st["plan_updated"], "2026-01-01T00:00:00Z")
        self.assertTrue(st["at"].endswith("Z"))

    def test_missing_row_gives_a_create_instruction(self):
        self.write()
        rows = self.good_rows()[:1]
        r = self.tracker("diff", "--actual", self.actual_file(rows))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("create row", r.stdout)
        self.assertIn("E-01.S3 Logout page", r.stdout)
        self.assertEqual(self.state()["drift"], 1)

    def test_stale_status_gives_a_set_instruction(self):
        self.write()
        rows = self.good_rows()
        rows[0]["Status"] = "Done"
        r = self.tracker("diff", "--actual", self.actual_file(rows))
        self.assertEqual(r.returncode, 1)
        self.assertIn("set Status of 'E-01.S2 Login page' to '", r.stdout)

    def test_stale_stage_gives_a_set_instruction(self):
        self.write()
        rows = self.good_rows()
        rows[1]["Stage"] = "building"
        r = self.tracker("diff", "--actual", self.actual_file(rows))
        self.assertEqual(r.returncode, 1)
        self.assertIn("set Stage of 'E-01.S3 Logout page' to 'intent'", r.stdout)

    def test_name_lacking_work_id_gives_a_rename_instruction(self):
        self.write()
        rows = self.good_rows()
        rows[0]["Name"] = "Login page"
        r = self.tracker("diff", "--actual", self.actual_file(rows))
        self.assertEqual(r.returncode, 1)
        self.assertIn("rename 'Login page' to start with its work id", r.stdout)
        self.assertNotIn("create row", r.stdout, "matched by title, not reported missing")

    def test_extra_row_is_flagged(self):
        self.write()
        rows = self.good_rows() + [{"Name": "E-09 Stray", "Status": "Done", "Stage": "recorded"}]
        r = self.tracker("diff", "--actual", self.actual_file(rows))
        self.assertEqual(r.returncode, 1)
        self.assertIn("row 'E-09 Stray' not in the plan: archive or add to the plan", r.stdout)

    def test_row_for_archived_done_work_is_not_an_extra(self):
        self.write()
        os.makedirs(os.path.join(self.dir, "plan", "archive"))
        json.dump([{"name": "E-00 Ancient", "period": "p", "outcome": "o"}],
                  open(os.path.join(self.dir, "plan", "archive", "done.json"), "w"))
        rows = self.good_rows() + [{"Name": "E-00 Ancient", "Status": "Done", "Stage": "recorded"}]
        r = self.tracker("diff", "--actual", self.actual_file(rows))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_duplicate_rows_are_flagged(self):
        self.write()
        rows = self.good_rows()
        rows.append(dict(rows[0]))
        r = self.tracker("diff", "--actual", self.actual_file(rows))
        self.assertEqual(r.returncode, 1)
        self.assertIn("duplicate", r.stdout)

    def test_unreadable_input_exits_2_and_records_nothing(self):
        self.write()
        cases = {"garbage": "{not json", "dict": '{"a": 1}', "scalar": "[1, 2]",
                 "no-name": '[{"Status": "Done"}]', "empty-file": ""}
        for label, raw in cases.items():
            r = self.tracker("diff", "--actual", self.actual_file(None, raw=raw))
            self.assertEqual(r.returncode, 2, (label, r.stdout, r.stderr))
        r = self.tracker("diff", "--actual", os.path.join(self.dir, "nope.json"))
        self.assertEqual(r.returncode, 2)
        r = self.tracker("diff")
        self.assertEqual(r.returncode, 2, "--actual is required")
        self.assertIsNone(self.state(), "an unreadable input is never recorded as a reconcile")

    def test_empty_list_is_readable_and_everything_is_missing(self):
        self.write()
        r = self.tracker("diff", "--actual", self.actual_file([]))
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout.count("create row"), 2)

    def test_expected_output_is_accepted_as_actual(self):
        self.write()
        exp = self.tracker("expected").stdout
        r = self.tracker("diff", "--actual", self.actual_file(None, raw=exp))
        self.assertEqual(r.returncode, 0, r.stdout)


class TestGate(TrackerBase):
    def test_never_reconciled_drifts_not_fails(self):
        self.write()
        _, fails, drifts = self.gate()
        self.assertEqual(tracker_msgs(fails), [], fails)
        self.assertEqual(len(tracker_msgs(drifts)), 1, drifts)
        self.assertIn("never", tracker_msgs(drifts)[0])

    def test_reconcile_clears_it_and_a_plan_edit_brings_it_back(self):
        self.write()
        rows = [{"Name": r["Name"], "Status": r["Status"], "Stage": r["Stage"]}
                for r in self.expected()["rows"]]
        self.tracker("diff", "--actual", self.actual_file(rows))
        _, fails, drifts = self.gate()
        self.assertEqual(tracker_msgs(fails + drifts), [], drifts)
        self.d["meta"]["updated"] = "2026-01-02T00:00:00Z"
        self.write()
        _, fails, drifts = self.gate()
        self.assertEqual(len(tracker_msgs(drifts)), 1, drifts)
        self.assertEqual(tracker_msgs(fails), [])

    def test_last_reconcile_with_unfixed_drift_still_drifts(self):
        self.write()
        self.tracker("diff", "--actual", self.actual_file([]))
        _, fails, drifts = self.gate()
        self.assertEqual(len(tracker_msgs(drifts)), 1, drifts)

    def test_work_id_naming_with_tracker_fails_on_unnamed_live_item(self):
        self.d["meta"]["naming"] = "work-ids"
        self.d["plans"]["next"] = [item("Tidy the docs")]
        self.write()
        code, fails, _ = self.gate()
        self.assertEqual(code, 1)
        self.assertEqual(len([f for f in fails if "work id" in f]), 1, fails)

    def test_tracker_without_naming_does_not_fail_unnamed_items(self):
        self.d["plans"]["next"] = [item("Tidy the docs")]
        self.write()
        _, fails, _ = self.gate()
        self.assertEqual([f for f in fails if "work id" in f], [])

    def test_malformed_tracker_fails(self):
        for bad in ({"kind": "nope", "target": "x"}, {"kind": "notion"}, {"target": "x"},
                    "notion", None, {"kind": "notion", "target": "x", "status_map": "no"},
                    {"kind": "notion", "target": "x", "recent_done": -1}):
            self.d["meta"]["tracker"] = bad
            self.write()
            _, fails, _ = self.gate()
            self.assertEqual(len(tracker_msgs(fails)), 1, (bad, fails))

    def test_light_mode_applies_it_too(self):
        self.d["meta"]["mode"] = "light"
        self.write()
        _, _, drifts = self.gate()
        self.assertEqual(len(tracker_msgs(drifts)), 1, drifts)


class TestSyncTracker(TrackerBase):
    def test_without_actual_prints_summary_and_next_step(self):
        self.write()
        r = run("sync.py", "--tracker", project=self.dir)
        self.assertIn("sync: tracker", r.stdout)
        self.assertIn("E-01.S2 Login page", r.stdout)
        self.assertIn("--actual", r.stdout)
        self.assertIn("notion", r.stdout)

    def test_with_actual_prints_the_diff_and_returns_1_on_drift(self):
        self.write()
        r = run("sync.py", "--tracker", "--actual", self.actual_file([]), project=self.dir)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("create row", r.stdout)

    def test_with_clean_actual_returns_0_and_gate_sees_the_record(self):
        self.write()
        rows = [{"Name": r["Name"], "Status": r["Status"], "Stage": r["Stage"]}
                for r in self.expected()["rows"]]
        r = run("sync.py", "--tracker", "--actual", self.actual_file(rows), project=self.dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("tracker reconcile", r.stdout.split("sync: tracker")[-1])

    def test_unreadable_actual_returns_2(self):
        self.write()
        r = run("sync.py", "--tracker", "--actual", self.actual_file(None, raw="{"), project=self.dir)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_flag_without_tracker_configured_returns_2(self):
        del self.d["meta"]["tracker"]
        self.write()
        r = run("sync.py", "--tracker", project=self.dir)
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
