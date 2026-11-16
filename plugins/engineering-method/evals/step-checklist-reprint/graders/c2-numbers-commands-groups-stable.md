---
type: llm
weight: 1
---

Scenario: steps are grouped under laptop, cloud console and new VM, each with its command.

Pass when the reprint keeps the original step numbers and commands in place, grouped by where they run.

Fail when steps are renumbered, merged, dropped or regrouped, or commands removed.
