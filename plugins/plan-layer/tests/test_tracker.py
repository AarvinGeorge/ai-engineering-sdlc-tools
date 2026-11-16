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

    def test_expected_object_shape_is_refused_as_actual(self):
        self.write()
        exp = self.tracker("expected").stdout
        r = self.tracker("diff", "--actual", self.actual_file(None, raw=exp))
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("from the tracker", r.stdout)
        self.assertIsNone(self.state(), "the gate cannot be cleared without the tracker")


class TestFixRound(TrackerBase):
    def good(self):
        return [{"Name": r["Name"], "Status": r["Status"], "Stage": r["Stage"]}
                for r in self.expected()["rows"]]

    def test_wrong_title_on_a_matching_id_is_a_rename(self):
        self.write()
        rows = self.good()
        rows[0]["Name"] = "E-01.S2 Totally different title"
        r = self.tracker("diff", "--actual", self.actual_file(rows))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("rename 'E-01.S2 Totally different title' to 'E-01.S2 Login page'", r.stdout)

    def test_older_done_row_not_marked_done_is_flagged(self):
        self.d["plans"]["done"] = [{"name": "E-00.S%d Old %d" % (i, i), "period": "p", "outcome": "o"}
                                   for i in range(8)]
        self.write()
        os.makedirs(os.path.join(self.dir, "plan", "archive"))
        with open(os.path.join(self.dir, "plan", "archive", "done.json"), "w") as fh:
            json.dump([{"name": "E-00.S99 Archived thing", "period": "p", "outcome": "o"}], fh)
        rows = self.good() + [{"Name": "E-00.S1 Old 1", "Status": "In progress", "Stage": "building"},
                              {"Name": "E-00.S99 Archived thing", "Status": "In progress", "Stage": "x"}]
        r = self.tracker("diff", "--actual", self.actual_file(rows))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("set Status of 'E-00.S1 Old 1' to 'Done'", r.stdout)
        self.assertIn("set Status of 'E-00.S99 Archived thing' to 'Done'", r.stdout)
        rows[-2]["Status"] = rows[-1]["Status"] = "Done"
        r = self.tracker("diff", "--actual", self.actual_file(rows))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_non_string_value_exits_2_naming_field_and_row(self):
        self.write()
        rows = self.good()
        rows[1]["Status"] = {"name": "In progress"}
        r = self.tracker("diff", "--actual", self.actual_file(rows))
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("Status", r.stdout)
        self.assertIn("E-01.S3 Logout page", r.stdout)
        self.assertIn("plain string", r.stdout)

    def test_adapters_tell_the_agent_to_flatten(self):
        for kind in ("notion", "generic"):
            with open(os.path.join(TRACKERS, kind + ".json")) as fh:
                self.assertIn("flatten every property to a plain string", json.load(fh)["fetch"])

    def write_adapter(self, kind, adapter):
        os.makedirs(os.path.join(self.dir, "plan", "trackers"), exist_ok=True)
        with open(os.path.join(self.dir, "plan", "trackers", kind + ".json"), "w") as fh:
            json.dump(adapter, fh)

    def linear(self, status_map=None):
        return {"fields": {"name": "Title", "status": "State"},
                "status_map": status_map or {"intent": "Backlog", "grounded": "Backlog",
                                             "planned": "Todo", "building": "In Progress",
                                             "verified": "In Review", "recorded": "In Review",
                                             "paused": "Paused", "done": "Done"}}

    def test_project_adapter_without_optional_fields(self):
        self.write_adapter("linear", self.linear())
        self.d["meta"]["tracker"] = {"kind": "linear", "target": "team"}
        self.write()
        rows = self.expected()["rows"]
        self.assertEqual(rows[0]["Title"], "E-01.S2 Login page")
        self.assertEqual(rows[0]["State"], "In Progress")
        self.assertEqual(set(rows[0]) - {"key"}, {"Title", "State"})
        act = [{"Title": r["Title"], "State": r["State"]} for r in rows]
        self.assertEqual(self.tracker("diff", "--actual", self.actual_file(act)).returncode, 0)
        act[0]["State"] = "Todo"
        r = self.tracker("diff", "--actual", self.actual_file(act))
        self.assertEqual(r.returncode, 1)
        self.assertIn("set State of 'E-01.S2 Login page' to 'In Progress'", r.stdout)
        _, fails, _ = self.gate()
        self.assertEqual(tracker_msgs(fails), [], fails)

    def test_project_adapter_is_checked_before_the_plugin_one(self):
        self.write_adapter("notion", self.linear({"intent": "Backlog", "grounded": "Backlog",
                                                  "planned": "Todo", "building": "Doing it",
                                                  "verified": "x", "recorded": "x",
                                                  "paused": "Paused", "done": "Done"}))
        self.write()
        self.assertEqual(self.expected()["rows"][0]["State"], "Doing it")

    def test_readme_documents_project_adapters_and_a_linear_example(self):
        with open(os.path.join(TRACKERS, "README.md")) as fh:
            text = fh.read()
        self.assertIn("plan/trackers/", text)
        self.assertIn("Linear", text)

    def test_no_plan_exits_2_for_diff(self):
        import shutil
        shutil.rmtree(os.path.join(self.dir, "plan"), ignore_errors=True)
        r = self.tracker("diff", "--actual", os.path.join(self.dir, "x.json"))
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("plan", r.stdout)

    def test_sync_returns_2_for_unreadable_input_even_when_gate_fails(self):
        self.d["plans"]["now"][0]["tasks"] = [{"name": "t", "state": "weird"}]
        self.write()
        r = run("sync.py", "--tracker", "--actual", self.actual_file(None, raw="{"), project=self.dir)
        self.assertIn("FAIL", r.stdout)
        self.assertEqual(r.returncode, 2, r.stdout)

    def test_sync_actual_without_tracker_is_usage(self):
        self.write()
        r = run("sync.py", "--actual", self.actual_file([]), project=self.dir)
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("--tracker", r.stdout)

    def test_separator_after_the_id_does_not_defeat_rename_matching(self):
        for sep in ("\u2014", "\u2013", ":", "\u00b7", "-"):
            self.d["plans"]["next"] = [item("E-01.S3 %s Caf\u00e9 na\u00efve search" % sep)]
            self.write()
            rows = [r for r in self.good() if r["Name"].startswith("E-01.S2")]
            rows.append({"Name": "Caf\u00e9 na\u00efve search", "Status": "Idea", "Stage": "intent"})
            r = self.tracker("diff", "--actual", self.actual_file(rows))
            self.assertEqual(r.returncode, 1, (sep, r.stdout))
            self.assertEqual(r.stdout.count("rename"), 1, (sep, r.stdout))
            self.assertNotIn("create row", r.stdout, sep)
            self.assertNotIn("not in the plan", r.stdout, sep)

    def test_same_name_without_ids_is_one_plan_problem(self):
        self.d["plans"]["next"] = [item("Tidy docs"), item("Tidy docs")]
        self.write()
        rows = [r for r in self.good() if r["Name"].startswith("E-01.S2")]
        rows.append({"Name": "Tidy docs", "Status": "Idea", "Stage": "intent"})
        r = self.tracker("diff", "--actual", self.actual_file(rows))
        self.assertEqual(r.stdout.count("share the name 'Tidy docs'"), 1, r.stdout)
        self.assertIn("give them work ids", r.stdout)
        self.assertNotIn("archive all but one", r.stdout)

    def test_utc_now_lives_in_plan_lib_only(self):
        import plan_lib
        self.assertRegex(plan_lib.utc_now(), r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        for f in ("check.py", "pause.py", "tracker.py"):
            with open(os.path.join(PLUGIN, "scripts", f)) as fh:
                self.assertNotIn("%Y-%m-%dT%H:%M:%SZ", fh.read(), f)


class TestGate(TrackerBase):
    def test_never_reconciled_drifts_not_fails(self):
        self.write()
        _, fails, drifts = self.gate()
        self.assertEqual(tracker_msgs(fails), [], fails)
        self.assertEqual(len(tracker_msgs(drifts)), 1, drifts)
        self.assertIn("never", tracker_msgs(drifts)[0])

    def reconcile_clean(self):
        rows = [{"Name": r["Name"], "Status": r["Status"], "Stage": r["Stage"]}
                for r in self.expected()["rows"]]
        r = self.tracker("diff", "--actual", self.actual_file(rows))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_reconcile_clears_it_and_a_change_to_a_row_brings_it_back(self):
        self.write()
        self.reconcile_clean()
        _, fails, drifts = self.gate()
        self.assertEqual(tracker_msgs(fails + drifts), [], drifts)
        self.d["plans"]["next"][0]["stage"] = "planned"
        self.write()
        _, fails, drifts = self.gate()
        self.assertEqual(len(tracker_msgs(drifts)), 1, drifts)
        self.assertEqual(tracker_msgs(fails), [])

    def test_unrelated_edit_does_not_force_a_refetch(self):
        self.write()
        self.reconcile_clean()
        self.d["meta"]["updated"] = "2026-01-02T00:00:00Z"
        self.d["parked"] = [{"id": "P1", "q": "q", "trigger": "t"}]
        self.write()
        _, fails, drifts = self.gate()
        self.assertEqual(tracker_msgs(fails + drifts), [], drifts)

    def test_pause_after_reconcile_drifts_even_in_the_same_second(self):
        self.write()
        self.reconcile_clean()
        self.d["meta"]["paused"] = {"at": "2026-01-01T00:00:00Z"}
        self.write()
        _, _, drifts = self.gate()
        self.assertEqual(len(tracker_msgs(drifts)), 1, drifts)

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
