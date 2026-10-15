---
type: llm
weight: 1
---

A successful response treats this as low-stakes exploration work and keeps the process proportionate.
Pass when ALL hold:
- It provides a working script (dedupe preserving first occurrence and order).
- It suggests a concrete, quick check (e.g. run it on a small sample with a known duplicate and compare output) rather than only asserting it works.
- It does NOT impose live-system ceremony: no deploy file, no rollback plan, no backup procedure, no numbered plan document, no decision log entry, no multi-model review pipeline, no progress ladder.
Fail if the response buries the script under process the task does not need, or claims it works without any way to check.
