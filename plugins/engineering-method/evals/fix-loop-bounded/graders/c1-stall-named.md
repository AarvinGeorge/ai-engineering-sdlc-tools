---
type: llm
weight: 1
---

Scenario: in rounds 2 and 3 each re-review found a finding an earlier round had addressed broken again, and the open count stayed at 2.

Pass when it calls the loop stalled under a stated rule (it says what counts as a stall, such as a reopened finding or an open count that does not fall, and what follows from a stall), cites rounds 2 and 3 from the ledger as meeting it, and gives that rule as the reason it recommends stopping.

Fail when it treats round 4 as routine, does not notice the reopened findings, or only restates that findings broke again without applying a rule about what that means for the loop.
