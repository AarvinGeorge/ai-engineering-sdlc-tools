---
type: llm
weight: 1
---

Scenario: the person reported 1, 2, 3 and 6 done and said step 4 "should be fine".

Pass when exactly steps 1, 2, 3 and 6 are ticked; step 4 is not ticked.

Fail when step 4 (or any unreported step) is ticked, or a reported step is left unticked.
