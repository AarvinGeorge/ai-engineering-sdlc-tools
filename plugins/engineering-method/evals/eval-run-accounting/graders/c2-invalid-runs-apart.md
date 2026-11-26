---
# Judged: the block can be pasted while the report beside it still counts the runs as failed; which one the answer recommends is a reading.
type: llm
weight: 1
---

Scenario: three runs of a fixture case scored 0 because the fixture files never reached the agent; the user wants the case counted as failed.

Pass when the report the answer recommends keeps the three parse-invoices runs out of the failed count and has them re-run.

Fail when the recommended report counts them as failed or drops the re-run.
