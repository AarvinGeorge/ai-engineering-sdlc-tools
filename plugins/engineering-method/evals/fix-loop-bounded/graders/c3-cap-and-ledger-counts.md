---
type: llm
weight: 1
---

Scenario: the user wants rounds to continue "until the reviewer says clean".

Pass when it declines the open-ended loop in one short pushback, states a round cap, says what happens to findings still open at the cap, and records each round with counts of findings closed, reopened and still open (or an equivalent stall marker).

Fail when it agrees to unbounded rounds, names a cap without saying what happens at it, or keeps the ledger without per-round counts.
