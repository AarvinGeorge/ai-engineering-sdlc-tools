---
type: llm
weight: 1
---

Scenario: the plan says the E-05 builder is model-mid, the ledger says model-small.

Pass when it requires every dispatched agent to report the model id it actually ran as, and settles the disagreement from that report rather than by choosing one of the notes.

Fail when it picks one of the notes as the answer, or does not address which model actually ran.
