---
type: llm
weight: 1
---

Scenario: the user plans a 15-minute recurring check of two lanes inside their main strongest-model session.

Pass when it moves the recurring check to a cheap agent (or a small script plus a cheap model) that reads lane state and writes the status, with the main session reading only that report.

Fail when it runs the recurring check in the main strongest-model session.
