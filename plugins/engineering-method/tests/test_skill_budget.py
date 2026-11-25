"""Budget and consistency checks for skills/engineering-method/SKILL.md.

What: fails when the skill body outgrows its word budget, the frontmatter
trigger text outgrows the harness limit, a stage-map cell grows past a pointer,
or the section 3 stage map drifts from scripts/method_hook.STAGES.
Use when: running the plugin's normal suite (python3 -m unittest discover tests).
Inputs: the files on disk. Output: unittest results. Side effects: none.
Role: enforces the "short body, detail in references" rule, so it does not
rest on anyone remembering a line count.
"""
import importlib.util
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
SKILL = os.path.join(PLUGIN, "skills", "engineering-method", "SKILL.md")
HOOK = os.path.join(PLUGIN, "scripts", "method_hook.py")

BODY_WORD_LIMIT = 2200
TRIGGER_CHAR_LIMIT = 1536
CELL_WORD_LIMIT = 25


def load_hook():
    spec = importlib.util.spec_from_file_location("method_hook", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def split_skill():
    with open(SKILL, encoding="utf-8") as fh:
        text = fh.read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise AssertionError("SKILL.md has no frontmatter block")
    return m.group(1), m.group(2)


def stage_rows(body):
    """Rows of the section 3 table as lists of stripped cells."""
    sec = re.search(r"^## 3\..*?$(.*?)^## 4\.", body, re.S | re.M)
    if not sec:
        raise AssertionError("SKILL.md has no section 3 followed by section 4")
    rows = []
    for line in sec.group(1).splitlines():
        if line.startswith("|") and not re.match(r"^\|\s*(Stage|-)", line):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


class SkillBudget(unittest.TestCase):
    def test_body_word_budget(self):
        _, body = split_skill()
        words = len(body.split())
        self.assertLessEqual(words, BODY_WORD_LIMIT, "SKILL.md body has %d words" % words)

    def test_trigger_text_within_harness_limit(self):
        front, _ = split_skill()
        fields = {}
        for key in ("description", "when_to_use"):
            m = re.search(r"^%s: (.*)$" % key, front, re.M)
            self.assertIsNotNone(m, "frontmatter lacks " + key)
            fields[key] = m.group(1)
        total = sum(len(v) for v in fields.values())
        self.assertLessEqual(total, TRIGGER_CHAR_LIMIT, "description + when_to_use = %d" % total)

    def test_stage_cells_are_pointers(self):
        _, body = split_skill()
        for row in stage_rows(body):
            words = len(row[-1].split())
            self.assertLessEqual(words, CELL_WORD_LIMIT, "stage %s cell has %d words" % (row[0], words))


class StageMapMatchesHook(unittest.TestCase):
    def test_rows_match_hook_stages(self):
        _, body = split_skill()
        rows = stage_rows(body)
        expected = [(s["stage"], s["skill"] or "(none)", s["references"]) for s in load_hook().STAGES]
        got = [(r[0], r[1].strip("`"), [x.strip() for x in r[2].split(",")]) for r in rows]
        self.assertEqual(got, expected)


class RuleCountsAgree(unittest.TestCase):
    """docs-and-decisions.md no longer miscounts principle 17's lines."""

    def test_no_five_steps_for_principle_17(self):
        ref = os.path.join(PLUGIN, "skills", "engineering-method", "references",
                           "docs-and-decisions.md")
        with open(ref, encoding="utf-8") as fh:
            self.assertNotIn("principle 17's five steps", fh.read())


if __name__ == "__main__":
    unittest.main()
