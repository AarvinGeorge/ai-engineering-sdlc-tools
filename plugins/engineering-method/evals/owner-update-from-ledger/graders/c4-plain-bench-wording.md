---
type: llm
weight: 1
---

Scenario: the ledger says "R-03 benched 14:10 UTC".

Pass when it does not use "benched" as a status word; it says the release was tested on the bench and passed, or equivalent plain wording.

Fail when the update says "benched" (quoting the ledger line verbatim as a cited source does not fail it if the update's own wording is plain).
