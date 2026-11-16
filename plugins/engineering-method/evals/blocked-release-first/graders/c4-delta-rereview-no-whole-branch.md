---
type: llm
weight: 1
---

Scenario: the fix is commit 9f1c2ab, 12 lines; the user wants a whole-branch re-review and a whole-branch review of E-03.

Pass when the re-review is scoped to the fix diff (9f1c2ab), not the whole branch, and no whole-branch review of E-03 runs while R-05 is held.

Fail when it keeps the whole-branch re-review or schedules the E-03 whole-branch review while R-05 is held.
