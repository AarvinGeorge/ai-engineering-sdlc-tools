"""Inventory parity (0.19.0): a declared inventory against every list that must cover it."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_light_and_budget import Base, SCRIPTS  # noqa: E402

AGENTS = ["agent-%02d" % i for i in range(1, 11)]


def inv(msgs):
    return [m for m in msgs if m.startswith("inventory ")]


class InvBase(Base):
    def put(self, rel, text):
        path = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(text)

    def setUp(self):
        super().setUp()
        self.put("ops/backup.sh", "for a in agent-01 agent-02 agent-03 agent-04 agent-05; do b $a; done\n")
        self.put("ops/copy.json", json.dumps({"jobs": [{"host": "host-a"}]}))
        self.d["inventory"] = {
            "agents": {"items": AGENTS, "covered_by": [{"list": "nightly backup", "file": "ops/backup.sh"}]},
            "hosts": {"items": ["host-a", "host-b"],
                      "covered_by": [{"list": "copy job", "file": "ops/copy.json", "json": "jobs[].host"}]},
        }


class TestParity(InvBase):
    def test_absent_inventory_is_silent(self):
        del self.d["inventory"]
        self.write()
        _, fails, drifts = self.gate()
        self.assertEqual(inv(fails + drifts), [])

    def test_backup_listing_five_of_ten_fails_naming_the_five(self):
        self.write()
        rc, fails, _ = self.gate()
        self.assertEqual(rc, 1)
        hit = [f for f in inv(fails) if "nightly backup" in f]
        self.assertEqual(len(hit), 1, fails)
        self.assertIn("5 of 10", hit[0])
        for a in AGENTS[5:]:
            self.assertIn(a, hit[0])

    def test_copy_job_covering_one_host_of_two_fails(self):
        self.write()
        _, fails, _ = self.gate()
        hit = [f for f in inv(fails) if "copy job" in f]
        self.assertTrue(hit and "host-b" in hit[0] and "1 of 2" in hit[0], fails)

    def test_full_coverage_is_clean_and_word_match_is_whole_word(self):
        self.put("ops/backup.sh", " ".join(AGENTS) + "\n")
        self.put("ops/copy.json", json.dumps({"jobs": [{"host": "host-a"}, {"host": "host-b"}]}))
        self.write()
        _, fails, _ = self.gate()
        self.assertEqual(inv(fails), [], fails)
        self.put("ops/backup.sh", " ".join(AGENTS[1:]).replace("agent-10", "agent-100") + " agent-010\n")
        self.write()
        _, fails, _ = self.gate()
        hit = inv(fails)[0]
        self.assertIn("agent-01", hit)
        self.assertIn("agent-10", hit)

    def test_exempt_needs_a_why(self):
        self.d["inventory"]["hosts"]["exempt"] = [{"item": "host-b", "list": "copy job", "why": "retiring"}]
        self.write()
        _, fails, _ = self.gate()
        self.assertFalse([f for f in inv(fails) if "copy job" in f], fails)
        self.d["inventory"]["hosts"]["exempt"] = [{"item": "host-b", "list": "copy job"}]
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "why" in f], fails)

    def test_unreadable_list_fails_loudly(self):
        self.d["inventory"]["hosts"]["covered_by"][0]["file"] = "ops/missing.json"
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "ops/missing.json" in f and "cannot read" in f], fails)

    def test_a_path_that_extracts_nothing_fails_never_passes(self):
        self.d["inventory"]["hosts"]["covered_by"][0]["json"] = "jobs[].hostname"
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "extracted nothing" in f], fails)

    def test_inventory_read_from_a_file(self):
        self.put("ops/agents.json", json.dumps({"agents": [{"name": a} for a in AGENTS]}))
        self.d["inventory"]["agents"]["items"] = None
        del self.d["inventory"]["agents"]["items"]
        self.d["inventory"]["agents"]["from"] = {"file": "ops/agents.json", "json": "agents[].name"}
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "5 of 10" in f], fails)

    def test_tracker_rows_as_a_covering_list(self):
        self.d["inventory"] = {"agents": {"items": ["agent-01", "agent-02"],
                                          "covered_by": [{"list": "tracker rows", "tracker": True}]}}
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "never reconciled" in f], fails)
        json.dump({"at": "2026-01-01T00:00:00Z", "actual_keys": ["agent-01"]},
                  open(os.path.join(self.dir, "plan", "tracker-state.json"), "w"))
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "agent-02" in f], fails)

    def test_malformed_inventory_fails(self):
        self.d["inventory"] = {"agents": {"items": AGENTS}}
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "covered_by" in f], fails)

    def test_a_bare_path_as_covering_list_fails_and_the_stop_hook_still_blocks(self):
        import subprocess, uuid
        self.d["inventory"]["hosts"]["covered_by"] = ["ops/copy.json"]
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "must be an object" in f], fails)
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.dir)
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "gate_hook.py")], cwd=self.dir,
                           env=env, input=json.dumps({"session_id": uuid.uuid4().hex}),
                           capture_output=True, text=True)
        self.assertEqual(json.loads(r.stdout).get("decision"), "block", r.stdout + r.stderr)

    def test_from_needs_a_json_path(self):
        del self.d["inventory"]["agents"]["items"]
        self.d["inventory"]["agents"]["from"] = {"file": "ops/backup.sh"}
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "from needs" in f], fails)

    def test_sentence_full_stop_after_a_name_still_counts(self):
        self.put("ops/backup.sh", "# covers " + ", ".join(AGENTS) + ".\n")
        self.write()
        _, fails, _ = self.gate()
        self.assertFalse([f for f in inv(fails) if "nightly backup" in f], fails)


class TestBoundaryAndTypes(InvBase):
    def only(self, text, item="agent-10"):
        self.put("ops/backup.sh", text + "\n")
        self.d["inventory"] = {"a": {"items": [item],
                                     "covered_by": [{"list": "bk", "file": "ops/backup.sh"}]}}
        self.write()
        _, fails, _ = self.gate()
        return inv(fails)

    def test_boundary_is_pinned(self):
        for bad in ("agent-10.b", "agent-10.env", "x.agent-10", "agent-10..env", "agent-10.-x"):
            self.assertTrue(self.only("see " + bad + " here"), bad)
        for ok in ("agent-10.", "agent-10, next", "(agent-10)", "agent-10.."):
            self.assertEqual(self.only("see " + ok), [], ok)

    def test_covering_entry_needs_file_or_tracker(self):
        self.d["inventory"]["hosts"]["covered_by"] = [{"list": "x"}]
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "file or tracker" in f], fails)

    def test_wrong_types_name_the_inventory_not_a_crash(self):
        cases = [{"item": 5, "list": "copy job", "why": "w"},
                 {"item": "host-b", "list": ["copy job"], "why": "w"},
                 {"item": "host-b", "list": "copy job", "why": 7}]
        for e in cases:
            self.d["inventory"]["hosts"]["exempt"] = [e]
            self.write()
            _, fails, _ = self.gate()
            self.assertTrue([f for f in inv(fails) if "'hosts'" in f and "exemption" in f], (e, fails))
            self.assertFalse([f for f in fails if "crashed" in f], fails)
        del self.d["inventory"]["hosts"]["exempt"]
        self.d["inventory"]["hosts"]["covered_by"] = [{"list": "tr", "tracker": True}]
        self.write()
        json.dump({"at": "2026-01-01T00:00:00Z", "actual_keys": "host-a"},
                  open(os.path.join(self.dir, "plan", "tracker-state.json"), "w"))
        _, fails, _ = self.gate()
        self.assertTrue([f for f in inv(fails) if "never reconciled" in f], fails)
        self.assertFalse([f for f in fails if "crashed" in f], fails)

    def test_a_boolean_is_not_an_extracted_name(self):
        self.put("ops/copy.json", json.dumps({"jobs": [{"host": True}, {"host": "host-a"}]}))
        self.d["inventory"]["hosts"]["items"] = ["host-a", "True"]
        self.write()
        _, fails, _ = self.gate()
        hit = [f for f in inv(fails) if "copy job" in f]
        self.assertTrue(hit and "True" in hit[0] and "1 of 2" in hit[0], fails)

    def test_exemption_naming_unknown_item_or_list_fails(self):
        for e in ({"item": "host-z", "list": "copy job", "why": "w"},
                  {"item": "host-b", "list": "no such list", "why": "w"}):
            self.d["inventory"]["hosts"]["exempt"] = [e]
            self.write()
            _, fails, _ = self.gate()
            self.assertTrue([f for f in inv(fails) if "unknown item or list" in f], (e, fails))
