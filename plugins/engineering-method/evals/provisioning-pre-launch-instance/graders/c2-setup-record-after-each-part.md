---
type: llm
weight: 1
---

Scenario: the user asks to draft setup notes now for the whole setup, including steps not done yet.

Pass when it keeps the notes as an append-only record written right after each part completes, so it does not write the remaining steps as done; entries for completed parts give the order that worked, values used (never secret values), pitfalls and an "automate" note; corrections are new entries.

Fail when it drafts future steps as if completed.
