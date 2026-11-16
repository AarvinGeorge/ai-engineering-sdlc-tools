---
type: llm
weight: 1
---

Scenario: six of seven bench stops were in helper scripts.

Pass when it treats the deploy helpers as code with tests and runs them in a pre-flight before the next bench run, off the bench: against saved real output (e.g. captured psql output) or a seeded throwaway database.

Fail when it offers only more care or review, with no pre-flight run of the helpers before the bench.
