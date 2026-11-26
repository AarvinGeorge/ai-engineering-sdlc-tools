---
# Judged: whether each grader choice fits its item and the reason given is a judgement over prose.
type: llm
weight: 1
---

Scenario: three items; item 1 is a file with a fixed heading, item 2 is a command run before a write, item 3 is readability.

Pass when items 1 and 2 are graded by checks computed from the run (for example a regex over the contents of NOTES.md or a file-exists check for item 1; a tool-order or tool-used check that the lint command ran before the write for item 2), an LLM judge is used only for item 3, and the answer says why code cannot decide item 3.

Fail when item 1 or item 2 is left to an LLM judge, or when no reason is given for judging item 3.
