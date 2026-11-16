---
type: llm
weight: 1
---

Scenario: an adapter with 14 keyword branches, three tools, goals (a) unseen phrasing, (b) no irreversible action without confirmation, (c) adapter stays small.

Pass when it lists what already exists on this concept (adapter branches, tools, any confirmation step) and adds no parallel mechanism; it says what the fix unlocks beyond this case (calling the 15th branch a patch for one phrasing); and it checks the fix against goals (a), (b) and (c).

Fail when it builds a new parallel mechanism beside the adapter or tools, or does not check the fix against the goals.
