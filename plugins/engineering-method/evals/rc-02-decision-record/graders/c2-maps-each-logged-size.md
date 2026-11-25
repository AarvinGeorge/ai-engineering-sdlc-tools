---
type: llm
weight: 1
---

Scenario: the log shows served=(612 + 0 + 940 chars) and the code shows the three parts are policy text, caller block and history.

Pass when it maps each of the three numbers to its part (612 policy text, 0 caller block, 940 history) and treats the empty caller block as the lead to follow first, before any prompt change.

Fail when it leaves the numbers undecoded, or adopts the teammate's prompt sentence without noticing the caller block was empty.
