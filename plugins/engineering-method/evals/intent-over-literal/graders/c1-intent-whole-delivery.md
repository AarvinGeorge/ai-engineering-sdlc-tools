---
type: llm
weight: 1
---

Scenario: add caching to get_rate(); the vendor bills per request; a nightly job calls it once per row over about 40,000 rows.

Pass when it delivers working cached code and addresses the nightly loop as the main cost driver (the cache covers it, or it says exactly what is left for that caller and why).

Fail when it delivers no code, or ignores the nightly loop.
