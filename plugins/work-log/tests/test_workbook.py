import os, sys, json, subprocess, tempfile, shutil, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
SCRIPTS = os.path.join(PLUGIN, "scripts")
sys.path.insert(0, SCRIPTS); sys.path.insert(0, HERE)
import zipfile, base64, hashlib
import xml.etree.ElementTree as ET
WB = os.path.join(SCRIPTS, "workbook.py")
try:
    import openpyxl
except ImportError:
    openpyxl = None

META = {"scope_name": "Alpha app", "period_start": "2026-10-26", "period_end": "2026-11-01", "kind": "weekly",
        "style": "hr", "tz": "America/New_York", "idle_minutes": 15,
        "sources": ["Claude Code transcripts", "git history"], "notes": ["Synthetic test note."],
        "missing_weeks": [{"start": "2026-10-12", "end": "2026-10-18"}]}
ENTRIES = [
    {"id": "E1", "date": "2026-10-26", "start": "10:00", "end": "11:30", "minutes": 44, "project": "Alpha app", "type": "Claude session", "summary": "Built the sign-in page."},
    {"id": "E2", "date": "2026-10-26", "start": "13:00", "end": "13:40", "minutes": 30, "project": "Beta site", "type": "Claude session", "summary": "Fixed the contact form."},
    {"id": "E3", "date": "2026-10-27", "start": "09:00", "end": "10:00", "minutes": 52, "project": "Alpha app", "type": "Claude session", "summary": "Added password reset."},
    {"id": "M1", "date": "2026-10-27", "start": "", "end": "", "stated_hours": 1.0, "project": "Capstone", "type": "Manual (hours stated)", "summary": "Call with the capstone team."}]

def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()

class Workbook(unittest.TestCase):
    def build(self, *flags, entries=None, meta=None):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d)
        p = os.path.join(d, "e.json")
        with open(p, "w") as fh:
            json.dump({"meta": meta or META, "entries": entries if entries is not None else ENTRIES}, fh)
        out = os.path.join(d, "o.xlsx")
        r = subprocess.run([sys.executable, WB, p, "--out", out, "--b64", out + ".b64", *flags], capture_output=True, text=True)
        return r, out

    def test_summary_and_rounding(self):
        r, out = self.build(); self.assertEqual(r.returncode, 0, r.stderr)
        s = json.loads(r.stdout)
        # 44 -> 0.75, 30 -> 0.5, 52 -> 0.75, manual 1.0
        self.assertEqual(s["day_totals"], {"2026-10-26": 1.25, "2026-10-27": 1.75})
        self.assertEqual(s["grand_total"], 3.0)
        self.assertEqual(s["tabs"], ["Entries", "Daily totals", "About"])
        self.assertEqual(s["title"], "Work log · Alpha app · 2026-10-26 to 2026-11-01")
        self.assertEqual(s["folder"], "Work Logs/Weekly")
        self.assertEqual(s["sha256"], hashlib.sha256(read_bytes(out)).hexdigest())
        self.assertEqual(base64.b64decode(read_bytes(out + ".b64")), read_bytes(out))

    def test_is_valid_zip_with_formulas(self):
        r, out = self.build()
        with zipfile.ZipFile(out) as z:
            self.assertIsNone(z.testzip())
            sheet2 = z.read("xl/worksheets/sheet2.xml").decode()
        self.assertIn("SUMIFS(Entries!$D:$D,Entries!$A:$A,$A2,Entries!$E:$E,$B2)", sheet2)
        self.assertIn("SUM(Entries!$D$2:$D$5)", sheet2)

    def test_half_quarter_rounds_up(self):
        r, _ = self.build(entries=[dict(ENTRIES[0], minutes=37.5)])
        self.assertEqual(json.loads(r.stdout)["grand_total"], 0.75)

    def test_deterministic(self):
        m = dict(META, created="2026-11-05T10:00 America/New_York")   # no minute-boundary flake
        r1, o1 = self.build(meta=m); r2, o2 = self.build(meta=m)
        self.assertEqual(read_bytes(o1), read_bytes(o2))

    @unittest.skipIf(openpyxl is None, "openpyxl not installed (test-only dependency)")
    def test_openpyxl_reads_tabs_and_cached_values(self):
        r, out = self.build()
        wb = openpyxl.load_workbook(out, data_only=True)
        self.assertEqual(wb.sheetnames, ["Entries", "Daily totals", "About"])
        e = wb["Entries"]
        self.assertEqual(e["D1"].value, "Estimated hours (from activity)")
        self.assertEqual([e.cell(row=i, column=8).value for i in range(2, 6)], ["E1", "E2", "E3", "M1"])
        dt = [tuple(c.value for c in row) for row in wb["Daily totals"].iter_rows(min_row=2)]
        self.assertIn(("2026-10-26", "All projects (day total)", 1.25), dt)
        self.assertEqual(dt[-1][0], "Grand total"); self.assertEqual(dt[-1][2], 3.0)
        about = {row[0].value: row[1].value for row in wb["About"].iter_rows(min_row=2)}
        self.assertEqual(about["Plugin version"], "0.1.0")
        self.assertTrue(any("2026-10-12 to 2026-10-18" in str(row[1].value) for row in wb["About"].iter_rows()))
        f = openpyxl.load_workbook(out)["Daily totals"]
        self.assertTrue(str(f["C2"].value).startswith("=SUMIFS("))

    @unittest.skipIf(openpyxl is None, "openpyxl not installed (test-only dependency)")
    def test_single_tab_fallback(self):
        r, out = self.build("--single-tab"); self.assertEqual(r.returncode, 0, r.stderr)
        wb = openpyxl.load_workbook(out)
        self.assertEqual(wb.sheetnames, ["Work log"])
        vals = [tuple(c.value for c in row) for row in wb["Work log"].iter_rows()]
        self.assertTrue(any(v[4] == "Day total" and v[3] == 1.25 for v in vals))
        self.assertFalse(any(isinstance(c, str) and c.startswith("=") for v in vals for c in v))
        self.assertTrue(any(v[0] == "Format" for v in vals))

    def test_escaping_and_control_chars(self):
        e = [dict(ENTRIES[0], summary='Fixed <tags> & "quotes"\x07 safely.')]
        r, out = self.build(entries=e); self.assertEqual(r.returncode, 0, r.stderr)
        with zipfile.ZipFile(out) as z:
            self.assertIn("&lt;tags&gt; &amp;", z.read("xl/worksheets/sheet1.xml").decode())

    def test_validation(self):
        for bad, needle in [([], "no entries"),
                            ([dict(ENTRIES[0], date="2026-11-09")], "E1"),
                            ([ENTRIES[0], ENTRIES[0]], "duplicate"),
                            ([dict(ENTRIES[0], type="Other")], "type")]:
            r, _ = self.build(entries=bad)
            self.assertEqual(r.returncode, 3); self.assertIn(needle, r.stderr)

    def test_manual_title_and_folder(self):
        m = dict(META, kind="manual", period_start="2026-10-27", period_end="2026-10-27")
        r, _ = self.build(entries=[ENTRIES[3]], meta=m)
        s = json.loads(r.stdout)
        self.assertEqual(s["folder"], "Work Logs/Manual"); self.assertTrue(s["title"].startswith("Work log manual entry · "))

    # --- added beyond the brief: package robustness for the Drive conversion ---

    def test_every_part_is_well_formed_xml(self):
        for flags in [(), ("--single-tab",)]:
            r, out = self.build(*flags); self.assertEqual(r.returncode, 0, r.stderr)
            with zipfile.ZipFile(out) as z:
                self.check_package(z)

    def check_package(self, z):
        names = z.namelist()
        self.assertEqual(names[0], "[Content_Types].xml")
        for req in ["[Content_Types].xml", "_rels/.rels", "xl/workbook.xml",
                    "xl/_rels/workbook.xml.rels", "xl/styles.xml", "xl/worksheets/sheet1.xml"]:
            self.assertIn(req, names)
        for n in names:
            ET.fromstring(z.read(n))   # raises on malformed XML
            self.assertEqual(z.getinfo(n).date_time, (1980, 1, 1, 0, 0, 0))
            self.assertEqual(z.getinfo(n).compress_type, zipfile.ZIP_DEFLATED)
        ct = z.read("[Content_Types].xml").decode()
        sheets = [n for n in names if n.startswith("xl/worksheets/")]
        for s in sheets:
            self.assertIn('PartName="/%s"' % s, ct)
        rels = z.read("xl/_rels/workbook.xml.rels").decode()
        self.assertEqual(rels.count("relationships/worksheet\""), len(sheets))

    def test_more_validation(self):
        for bad, needle in [([dict(ENTRIES[0], minutes=-1)], "minutes"),
                            ([dict(ENTRIES[3], stated_hours=-0.5)], "stated_hours"),
                            ([dict(ENTRIES[0], date="2026/10/26")], "date")]:
            r, _ = self.build(entries=bad)
            self.assertEqual(r.returncode, 3, r.stdout); self.assertIn(needle, r.stderr)

    def test_default_out_uses_title_in_cwd(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d)
        p = os.path.join(d, "e.json")
        with open(p, "w") as fh:
            json.dump({"meta": META, "entries": ENTRIES}, fh)
        r = subprocess.run([sys.executable, WB, p], capture_output=True, text=True, cwd=d)
        self.assertEqual(r.returncode, 0, r.stderr)
        expect = os.path.join(d, "Work log · Alpha app · 2026-10-26 to 2026-11-01.xlsx")
        self.assertTrue(os.path.isfile(expect), os.listdir(d))
        self.assertEqual(os.path.realpath(json.loads(r.stdout)["path"]), os.path.realpath(expect))

    # --- fix round 1 ---

    def test_project_required(self):
        for proj in ["", "   ", None]:
            r, _ = self.build(entries=[dict(ENTRIES[1], project=proj)])
            self.assertEqual(r.returncode, 3, r.stdout)
            self.assertIn("E2", r.stderr); self.assertIn("project", r.stderr)
        e = dict(ENTRIES[1]); del e["project"]
        r, _ = self.build(entries=[e]); self.assertEqual(r.returncode, 3); self.assertIn("project", r.stderr)

    def test_out_into_missing_dir_is_clean_exit(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d)
        p = os.path.join(d, "e.json")
        with open(p, "w") as fh:
            json.dump({"meta": META, "entries": ENTRIES}, fh)
        for args in (["--out", os.path.join(d, "nope", "o.xlsx")],
                     ["--out", os.path.join(d, "o.xlsx"), "--b64", os.path.join(d, "nope", "o.b64")]):
            r = subprocess.run([sys.executable, WB, p, *args], capture_output=True, text=True)
            self.assertEqual(r.returncode, 3, r.stderr)
            self.assertNotIn("Traceback", r.stderr)
            self.assertEqual(len(r.stderr.strip().splitlines()), 1, r.stderr)

    def test_unknown_tz_notes_and_continues(self):
        r, _ = self.build(meta=dict(META, tz="Mars/Olympus_Mons"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Mars/Olympus_Mons", r.stderr)
        self.assertEqual(len(r.stderr.strip().splitlines()), 1, r.stderr)

if __name__ == "__main__":
    unittest.main()
