"""0.17.0: opt-in work-id naming. With meta.naming = "work-ids", every item in
plans.now and plans.next must be named from an epic, story, task, finding or
release id (E-01, E-01.S2, E-01.S2.T3, E-01.F1, R-04). Absent means no check,
so every plan written before 0.17.0 is unchanged."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import plan_lib as L  # noqa: E402
from test_light_and_budget import Base  # noqa: E402


def item(name, stage="intent"):
    return {"name": name, "why": "w", "unblocks": "u", "stage": stage, "plan_file": None}


def naming_fails(fails):
    return [f for f in fails if "work id" in f or "meta.naming" in f]


class TestWorkIdPattern(unittest.TestCase):
    def test_accepted_forms(self):
        for n in ("E-01 search", "E-01.S2 slice", "E-01.S2.T3 one step", "E-12.F4 fix the cap",
                  "R-07 release", "E-101 three digits", "E-01", "E-01.S2: colon", "E-01 · dot"):
            self.assertTrue(L.has_work_id(n), n)

    def test_rejected_forms(self):
        for n in ("Search for E-01", "e-01 lower case", "E-1 one digit", "E-01x glued",
                  "R-7", "Round 1e", "I-1 initiative is not a work item", "D-001 a decision",
                  "", None, "E-01.S slice without number"):
            self.assertFalse(L.has_work_id(n), repr(n))


class TestNamingGate(Base):
    def test_absent_means_no_check(self):
        self.d["plans"]["next"] = [item("First thing to do")]
        self.write()
        _, fails, _ = self.gate()
        self.assertEqual(naming_fails(fails), [], fails)

    def test_opted_in_plan_with_ids_passes(self):
        self.d["meta"]["naming"] = "work-ids"
        self.d["plans"]["next"] = [item("E-01 search"), item("R-02 E-01.S2 ship the slice")]
        self.write()
        _, fails, _ = self.gate()
        self.assertEqual(naming_fails(fails), [], fails)

    def test_opted_in_next_item_without_id_fails(self):
        self.d["meta"]["naming"] = "work-ids"
        self.d["plans"]["next"] = [item("E-01 search"), item("Tidy the docs")]
        self.write()
        code, fails, _ = self.gate()
        nf = naming_fails(fails)
        self.assertEqual(len(nf), 1, fails)
        self.assertIn("Tidy the docs", nf[0])
        self.assertEqual(code, 1)

    def test_opted_in_now_item_without_id_fails(self):
        self.d["meta"]["naming"] = "work-ids"
        self.d["plans"]["now"] = [dict(item("Build the exporter", "planned"),
                                       plan_file="docs/01_plan.md",
                                       tasks=[{"name": "t", "state": "todo"}])]
        self.d["plans"]["next"] = []
        self.write()
        _, fails, _ = self.gate()
        nf = naming_fails(fails)
        self.assertEqual(len(nf), 1, fails)
        self.assertIn("Build the exporter", nf[0])

    def test_done_items_are_not_held_to_it(self):
        self.d["meta"]["naming"] = "work-ids"
        self.d["plans"]["next"] = [item("E-01 search")]
        self.d["plans"]["done"] = [{"name": "old round 1a", "period": "2026-01-01", "outcome": "o"}]
        self.write()
        _, fails, _ = self.gate()
        self.assertEqual(naming_fails(fails), [], fails)

    def test_unknown_naming_value_fails(self):
        self.d["meta"]["naming"] = "jira"
        self.write()
        _, fails, _ = self.gate()
        self.assertTrue(any("meta.naming" in f for f in fails), fails)

    def test_light_mode_applies_it_too(self):
        self.d["meta"]["mode"] = "light"
        self.d["meta"]["naming"] = "work-ids"
        self.d["plans"]["next"] = [item("no id here")]
        self.write()
        _, fails, _ = self.gate()
        self.assertEqual(len(naming_fails(fails)), 1, fails)


if __name__ == "__main__":
    unittest.main()
