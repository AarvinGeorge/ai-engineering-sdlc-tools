"""Structure checks for references/root-cause-investigation.md.

What: fails when a step heading is missing, duplicated or out of order, a step
lacks one of its fields, or the reference stops pointing at systematic-debugging.
Use when: running the plugin's normal suite.
Inputs: the reference on disk. Output: unittest results. Side effects: none.
Role: keeps the ten steps invocable by name and in the house form.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(os.path.dirname(HERE), "skills", "engineering-method",
                   "references", "root-cause-investigation.md")
NAMES = ["Pin what ran", "Read the decision record", "Read the full input",
         "Quote the objection", "Diff the served inputs", "Inventory the concept",
         "Trace the dropped fact", "Label the root, then fit the fix",
         "Close the loop", "Brief the investigator blind"]
FIELDS = ("**Rule.**", "**Trigger:**", "**Input:**", "**Output:**", "**Prevents:**",
          "**Evidence:**", "*Why:*", "*Test:*")


def read():
    with open(REF, encoding="utf-8") as fh:
        return fh.read()


def blocks(text):
    parts = re.split(r"^### (RC-\d+) ", text, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


class RootCauseReference(unittest.TestCase):
    def test_every_step_once_in_order(self):
        heads = re.findall(r"^### (RC-\d+) (.+?)(?: \(LLM\))?$", read(), re.M)
        self.assertEqual(heads, [("RC-%d" % (i + 1), n) for i, n in enumerate(NAMES)])

    def test_each_step_has_every_field(self):
        for name, body in blocks(read()).items():
            for field in FIELDS:
                self.assertIn(field, body, "%s lacks %s" % (name, field))

    def test_points_at_superpowers_not_restating_it(self):
        text = read()
        self.assertIn("superpowers:systematic-debugging", text)
        self.assertNotIn("NO FIXES WITHOUT ROOT CAUSE", text)

    def test_opens_with_evidence_before_any_cause(self):
        """The first lines under the title are the ordering rule, before anything else."""
        body = read().split("\n", 1)[1].lstrip("\n")
        first = body.split("\n\n", 1)[0]
        self.assertTrue(first.startswith("**Evidence before any cause"), first[:80])
        for word in ("RC-1", "RC-4", "RC-5", "`done`", "`requested`", "`skipped`",
                     "No cause, suspect list or fix"):
            self.assertIn(word, first)

    def test_names_its_departures(self):
        self.assertRegex(read(), r"(?m)^## Where this departs from systematic-debugging")


if __name__ == "__main__":
    unittest.main()
