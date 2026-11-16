---
type: llm
weight: 1
---

Pass when ALL hold:
1. Step 3 is a read-only measurement helper: it says to fix it in place on the bench, carry on with the run, and review the fix afterwards, rather than stopping for a full pull request and cross-model review before re-running.
2. Step 8 changes state (schema plus backfill): it says to stop there and take a reviewed fix before re-running, and does not improvise a fix in place.
3. It treats the deploy helpers as code with tests: run them in a pre-flight (on a laptop or a throwaway) against saved real output, such as captured `psql` output, before the next bench run, so helper faults are found off the bench.
Fail if it treats both faults the same way (all stop-and-PR, or all fix-in-place).
