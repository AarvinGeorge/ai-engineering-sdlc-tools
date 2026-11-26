"""Checks the permission-profile snippets in references/permission-profiles.md.

What: parses every fenced json block in the reference and checks each is
pasteable and matches the rules Claude Code documents.
Use when: running the plugin's normal suite (python3 -m unittest discover tests).
Inputs: the reference file on disk. Output: unittest results. Side effects: none.
Role: keeps "deny wins, cumulative per tier" a checked claim, not prose.
"""
import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(os.path.dirname(HERE), "skills", "engineering-method", "references",
                   "permission-profiles.md")
TIERS = ("exploration", "internal", "live")
RULE = re.compile(r"^[A-Z][A-Za-z0-9]*(\([^()]+\))?$")  # no bare *, no lowercase tool, no nested ()


def profiles():
    """Return {tier: parsed json} for blocks fenced ```json and headed '### <tier>'."""
    with open(REF, encoding="utf-8") as fh:
        text = fh.read()
    out = {}
    for m in re.finditer(r"^### (\w+)[^\n]*\n(?:(?!^### ).)*?```json\n(.*?)\n```", text, re.S | re.M):
        out[m.group(1).lower()] = json.loads(m.group(2))
    return out


class Snippets(unittest.TestCase):
    def test_one_snippet_per_tier(self):
        self.assertEqual(sorted(profiles()), sorted(TIERS))

    def test_rules_have_the_documented_form(self):
        for tier, d in profiles().items():
            perms = d["permissions"]
            for key in ("allow", "ask", "deny"):
                for rule in perms.get(key, []):
                    self.assertRegex(rule, RULE, "%s %s: %r" % (tier, key, rule))
                    self.assertNotIn("(command:", rule, "parameter rules on command are ignored")

    def test_no_mode_a_project_file_cannot_set(self):
        for tier, d in profiles().items():
            self.assertNotIn(d["permissions"].get("defaultMode"), ("bypassPermissions", "auto"), tier)

    def test_deny_and_ask_are_cumulative(self):
        p = profiles()
        for key in ("deny", "ask"):
            lo, mid, hi = (set(p[t]["permissions"].get(key, [])) for t in TIERS)
            self.assertLessEqual(lo, mid, "internal %s drops an exploration rule" % key)
            self.assertLessEqual(mid, hi, "live %s drops an internal rule" % key)

    def test_live_disables_bypass(self):
        self.assertEqual(profiles()["live"]["permissions"].get("disableBypassPermissionsMode"),
                         "disable")


if __name__ == "__main__":
    unittest.main()
