import os, sys, json, subprocess, tempfile, shutil, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
SCRIPTS = os.path.join(PLUGIN, "scripts")
sys.path.insert(0, SCRIPTS); sys.path.insert(0, HERE)
from datetime import date
import periods as P
import workbook as W
def t(a, b, scope="Alpha app"): return f"Work log · {scope} · {a} to {b}"

class Periods(unittest.TestCase):
    def test_last_week_from_any_weekday(self):
        for today in [date(2026, 11, 2), date(2026, 11, 5), date(2026, 11, 8)]:
            self.assertEqual(P.last_week(today), (date(2026, 10, 26), date(2026, 11, 1)))

    def test_first_run_only_last_week(self):
        r = P.missing_weeks([], "Alpha app", date(2026, 11, 9), date(2026, 10, 1))
        self.assertEqual([w["start"] for w in r["to_create"]], ["2026-11-02"])
        self.assertEqual(r["to_create"][0]["title"], t("2026-11-02", "2026-11-08"))

    def test_gap_fill_after_missed_mondays(self):
        r = P.missing_weeks([t("2026-10-12", "2026-10-18")], "Alpha app", date(2026, 11, 10), date(2026, 10, 6))
        self.assertEqual([w["start"] for w in r["to_create"]], ["2026-10-19", "2026-10-26", "2026-11-02"])

    def test_idempotent_when_saved(self):
        r = P.missing_weeks([t("2026-11-02", "2026-11-08")], "Alpha app", date(2026, 11, 9), date(2026, 10, 1))
        self.assertEqual(r["to_create"], []); self.assertEqual(r["already_saved"], ["2026-11-02"])

    def test_other_scopes_and_non_week_titles_ignored(self):
        titles = [t("2026-11-02", "2026-11-08", "Beta site"), t("2026-11-03", "2026-11-05"),
                  "Work log manual entry · Alpha app · 2026-11-03 to 2026-11-03"]
        r = P.missing_weeks(titles, "Alpha app", date(2026, 11, 9), date(2026, 10, 1))
        self.assertEqual([w["start"] for w in r["to_create"]], ["2026-11-02"])

    def test_unrecoverable_and_partial(self):
        r = P.missing_weeks([t("2026-09-21", "2026-09-27")], "Alpha app", date(2026, 10, 20), date(2026, 10, 8))
        self.assertEqual([w["start"] for w in r["unrecoverable"]], ["2026-09-28"])
        self.assertEqual([(w["start"], w["partial"]) for w in r["to_create"]],
                         [("2026-10-05", True), ("2026-10-12", False)])

    def test_cap(self):
        r = P.missing_weeks([t("2025-01-06", "2025-01-12")], "Alpha app", date(2026, 11, 9), date(2025, 1, 1), max_weeks=8)
        self.assertEqual(len(r["to_create"]), 8); self.assertEqual(r["to_create"][-1]["start"], "2026-11-02")
        total = len(r["to_create"]) + len(r["skipped_by_cap"]) + len(r["unrecoverable"])
        self.assertEqual(total, 95)    # every Monday 2025-01-13 .. 2026-11-02 is accounted for

    def test_cap_does_not_hide_unrecoverable(self):
        r = P.missing_weeks([t("2026-06-01", "2026-06-07")], "Alpha app", date(2026, 11, 9), date(2026, 10, 10))
        self.assertEqual(r["unrecoverable"][0]["start"], "2026-06-08")
        self.assertEqual(r["unrecoverable"][-1]["start"], "2026-09-28")
        self.assertEqual([w["start"] for w in r["to_create"]], ["2026-10-05", "2026-10-12", "2026-10-19", "2026-10-26", "2026-11-02"])

    def test_no_transcripts_everything_unrecoverable(self):
        r = P.missing_weeks([t("2026-10-19", "2026-10-25")], "Alpha app", date(2026, 11, 9), None)
        self.assertEqual(r["to_create"], [])
        self.assertEqual([w["start"] for w in r["unrecoverable"]], ["2026-10-26", "2026-11-02"])

    def test_workbook_title_is_recognised(self):
        meta = {"scope_name": "Alpha app", "period_start": "2026-10-26", "period_end": "2026-11-01", "kind": "weekly"}
        self.assertEqual(P.saved_weeks([W.title_of(meta)], "Alpha app"), {date(2026, 10, 26)})
        # and a title this module builds is what workbook builds
        r = P.missing_weeks([], "Alpha app", date(2026, 11, 5), date(2026, 10, 1))
        self.assertEqual(r["to_create"][0]["title"], W.title_of(meta))

    def test_cli(self):
        out = subprocess.run([sys.executable, os.path.join(SCRIPTS, "periods.py"), "last-week", "--today", "2026-11-05"],
                             capture_output=True, text=True)
        self.assertEqual(json.loads(out.stdout), {"start": "2026-10-26", "end": "2026-11-01"})

    def test_cli_missing_weeks_stdin(self):
        out = subprocess.run([sys.executable, os.path.join(SCRIPTS, "periods.py"), "missing-weeks", "--scope-name", "Alpha app",
                              "--today", "2026-11-09", "--earliest", "2026-10-01", "--titles-json", "-"],
                             input="[]", capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout)["to_create"][0]["start"], "2026-11-02")

if __name__ == "__main__":
    unittest.main()


class FixRound1(unittest.TestCase):
    def test_single_tab_fallback_counts_as_saved(self):
        r = P.missing_weeks([t("2026-11-02", "2026-11-08") + " (single tab)"], "Alpha app",
                            date(2026, 11, 9), date(2026, 10, 1))
        self.assertEqual(r["to_create"], []); self.assertEqual(r["already_saved"], ["2026-11-02"])

    def test_other_suffixes_and_trailing_newline_not_saved(self):
        for title in [t("2026-11-02", "2026-11-08") + " (2)", t("2026-11-02", "2026-11-08") + "\n",
                      t("2026-11-02", "2026-11-08") + " (single tab)\n"]:
            r = P.missing_weeks([title], "Alpha app", date(2026, 11, 9), date(2026, 10, 1))
            self.assertEqual([w["start"] for w in r["to_create"]], ["2026-11-02"], repr(title))

    def test_cli_non_string_title_is_exit_3(self):
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "periods.py"), "missing-weeks",
                            "--scope-name", "Alpha app", "--today", "2026-11-09", "--titles-json", "-"],
                           input=json.dumps([t("2026-11-02", "2026-11-08"), 7]), capture_output=True, text=True)
        self.assertEqual(r.returncode, 3, r.stderr); self.assertNotIn("Traceback", r.stderr)
