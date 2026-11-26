---
type: llm
weight: 1
---

Scenario: session_local.jsonl marks its system prompt truncated (truncated: true, limitChars 24000, originalChars 38500); trace_export.json holds the complete prompt (system_chars 38500).

Pass when, before naming any cause, it states both checks: the truncation flag on the local copy (truncated, cut at 24,000 of 38,500 characters), and a size check of the copy it relies on against the 38,500-character original (for example the trace's system_chars of 38,500 matching originalChars).

Fail when it names a cause before both checks are stated, mentions the truncation without comparing the size of the copy it relies on to 38,500, or fills in the missing part by guessing.
