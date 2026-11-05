import os, sys, json, subprocess, tempfile, shutil, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
SCRIPTS = os.path.join(PLUGIN, "scripts")
sys.path.insert(0, SCRIPTS); sys.path.insert(0, HERE)
from zoneinfo import ZoneInfo
import collect, wl_common as C

def T(s): return C.parse_ts(s)

class Time(unittest.TestCase):
    def test_parse_z_and_offset_equal(self):
        self.assertEqual(T("2026-10-26T14:00:00Z"), T("2026-10-26T09:00:00-05:00"))
        self.assertEqual(T("2026-10-26T14:00:00.500Z") - T("2026-10-26T14:00:00Z"), 0.5)
        with self.assertRaises(ValueError): T("yesterday")

    def test_idle_gap_dropped(self):
        ts = [T("2026-10-26T10:00:00Z"), T("2026-10-26T10:10:00Z"),   # 10 min kept
              T("2026-10-26T10:40:00Z"),                              # 30 min gap dropped
              T("2026-10-26T10:45:00Z")]                              # 5 min kept
        iv = collect.active_intervals(ts, 15 * 60)
        self.assertEqual(sum(b - a for a, b in iv), 15 * 60)

    def test_gap_exactly_at_cutoff_kept(self):
        ts = [T("2026-10-26T10:00:00Z"), T("2026-10-26T10:15:00Z")]
        self.assertEqual(collect.active_intervals(ts, 900), [(ts[0], ts[1])])

    def test_single_message_is_zero(self):
        self.assertEqual(collect.active_intervals([T("2026-10-26T10:00:00Z")], 900), [])

    def test_midnight_split_local(self):
        tz = ZoneInfo("America/New_York")   # 23:50 to 00:10 local on 26/27 Oct (EDT, -4)
        a, b = T("2026-10-27T03:50:00Z"), T("2026-10-27T04:10:00Z")
        parts = collect.split_days((a, b), tz)
        self.assertEqual([(d, round(y - x)) for d, x, y in parts],
                         [("2026-10-26", 600), ("2026-10-27", 600)])

    def test_dst_day_split(self):
        tz = ZoneInfo("America/New_York")   # DST ends 1 Nov 2026 02:00 local
        a, b = T("2026-11-01T03:30:00Z"), T("2026-11-01T06:30:00Z")   # 23:30 EDT -> 01:30 EST
        parts = collect.split_days((a, b), tz)
        self.assertEqual([d for d, _, _ in parts], ["2026-10-31", "2026-11-01"])
        self.assertEqual(round(parts[0][2] - parts[0][1]), 1800)

    def test_overlap_counted_once(self):
        a = [(T("2026-10-26T10:00:00Z"), T("2026-10-26T11:00:00Z"))]
        b = [(T("2026-10-26T10:30:00Z"), T("2026-10-26T11:30:00Z"))]
        got = collect.allocate({"s1": a, "s2": b})
        self.assertAlmostEqual(sum(got.values()), 90 * 60)          # union, not 120
        self.assertAlmostEqual(got["s1"], 45 * 60)                  # 30 alone + 15 shared
        self.assertAlmostEqual(got["s2"], 45 * 60)

    def test_project_name(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d)
        repo = os.path.join(d, "alpha-app"); os.makedirs(os.path.join(repo, ".git"))
        os.makedirs(os.path.join(repo, "src", "ui"))
        self.assertEqual(C.project_name(os.path.join(repo, "src", "ui"), {}), "Alpha app")
        self.assertEqual(C.project_name(repo + "/.claude/worktrees/x-1", {}), "Alpha app")
        self.assertEqual(C.project_name(repo, {repo: "Alpha (client)"}), "Alpha (client)")
        self.assertEqual(C.project_name("/home/dev/beta_site", {}), "Beta site")

    def test_local_zone_explicit(self):
        tz, name = C.local_zone("Europe/London")
        self.assertEqual(name, "Europe/London")

    def test_version(self):
        self.assertEqual(C.plugin_version(), "0.1.0")

    def test_project_name_empty_falls_back(self):
        for p in ("/", "//", "/home/dev/---", "/home/dev/_._", ""):
            self.assertEqual(C.project_name(p, {}), "Unknown project", p)

    def test_allocate_nested_and_disjoint(self):
        got = collect.allocate({"a": [(0, 100), (200, 300)], "b": [(50, 60)], "c": [(400, 400)], "d": []})
        self.assertAlmostEqual(got["a"], 95 + 100)
        self.assertAlmostEqual(got["b"], 5)
        self.assertEqual((got["c"], got["d"]), (0.0, 0.0))

    def test_allocate_scales(self):
        import random, time as _t
        rnd = random.Random(7)
        per = {}
        for s in range(500):
            t, ivs = rnd.randint(0, 10000), []
            for _ in range(50):
                a = t + rnd.randint(0, 300); b = a + rnd.randint(1, 900); ivs.append((a, b)); t = b
            per["s%d" % s] = ivs
        t0 = _t.perf_counter(); got = collect.allocate(per); took = _t.perf_counter() - t0
        self.assertLess(took, 10.0)
        events = sorted(iv for ivs in per.values() for iv in ivs)
        union, cur = 0, None
        for a, b in events:
            if cur is None or a > cur[1]:
                if cur: union += cur[1] - cur[0]
                cur = [a, b]
            else:
                cur[1] = max(cur[1], b)
        union += cur[1] - cur[0]
        self.assertAlmostEqual(sum(got.values()), union, places=3)
