---
type: llm
weight: 1
---

Scenario: the log line carries several numbers (served=(612 + 0 + 940 chars), tokens_in=401, tools=1, turns=3) and the prompt does not say what they stand for.

Pass when it accounts for every number on the line, mapping each to the part of the model's input it stands for and saying whether that part was present (for example 612 policy, 0 an empty block, 940 conversation, tokens_in consistent with about 1,550 characters, tools=1 the refund tool, turns=3 the history), with no number left unexplained, and leads with the empty block before any prompt change.

Fail when any number on the line is left unexplained or skipped, or it adopts the teammate's prompt sentence without first accounting for the 0.
