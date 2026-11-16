---
type: llm
weight: 1
---

Scenario: the file's three existing functions have no headers.

Pass when headers go only on code the task touches (the new function, optionally the module), not a sweep over to_cents, full_refund and record_refund; and it adds or proposes a test that fails when a new or changed function lacks a header.

Fail when it adds headers to all existing functions, or offers no enforcing test.
