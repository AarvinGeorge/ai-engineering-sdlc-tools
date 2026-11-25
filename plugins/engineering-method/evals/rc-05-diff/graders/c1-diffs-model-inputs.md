---
type: llm
weight: 1
---

Scenario: the same booking request is confirmed on one instance and refused on another.

Pass when it asks for or performs a block-by-block comparison of the full model inputs actually given to a working run and a failing run (system prompt, tool definitions, retrieved data, history), not only of the user messages or configuration.

Fail when it does not compare the model inputs of a working and a failing run, or compares only the message text.
