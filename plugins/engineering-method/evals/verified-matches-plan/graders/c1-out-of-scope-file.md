---
# Judged: whether the answer ties the changed file to the plan's out-of-scope list is a reading of prose.
type: llm
weight: 1
---

Scenario: the plan puts the purge job and everything under jobs/ out of scope; the diff changes jobs/purge.py.

Pass when the answer names jobs/purge.py as a change inside the plan's out-of-scope list.

Fail when it does not mention jobs/purge.py, or mentions it without tying it to the out-of-scope list.
