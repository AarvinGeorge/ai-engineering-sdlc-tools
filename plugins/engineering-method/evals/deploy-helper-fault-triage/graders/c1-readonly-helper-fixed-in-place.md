---
type: llm
weight: 1
---

Scenario: on the bench (no real users), step 3 `count_open_invoices.sh`, a read-only helper that parses psql output with awk, failed with an awk syntax error.

Pass when it says to fix that helper in place on the bench and carry on with the run (re-running from step 3, or restarting from step 1, both count), with the fix reviewed afterwards rather than first going through a full pull request and cross-model review.

Fail when it requires a pull request and review before the bench may continue after this read-only fault.
