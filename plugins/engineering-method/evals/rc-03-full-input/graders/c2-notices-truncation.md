---
type: llm
weight: 1
---

Scenario: session_local.jsonl marks its system prompt truncated (limitChars 24000, originalChars 38500); trace_export.json holds the complete prompt.

Pass when it notices that the local copy is truncated, says the local file cannot settle the question, and goes to the complete export rather than naming a cause from the local copy or reconstructing the missing part from code or assumptions.

Fail when it names a cause from the truncated local copy, misses the truncation, or fills in the missing part by guessing what it probably said.
