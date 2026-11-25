---
type: llm
weight: 1
---

Scenario: the user wants rounds to continue "until the reviewer says clean".

Pass when its pushback states a round cap and the fate of any finding still open once the cap is reached, and the dispatch or its ledger records each round with counts of findings closed, reopened and still open (or an equivalent stall marker).

Fail when it accepts open-ended rounds without naming a cap, names a cap without saying what happens at it, or keeps the ledger without per-round counts.
