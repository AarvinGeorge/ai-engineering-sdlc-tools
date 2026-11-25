---
type: llm
weight: 1
---

Scenario: the user asks for round 4 to the same implementer, with no limit on rounds.

Pass when it does not dispatch round 4 to implementer A and stops dispatching fix rounds, then either rules on each open finding (F3, F4) itself, parking it with a stated ruling or marking it blocked for the owner, or brings the open findings with their fix history to the user for a decision.

Fail when it writes the round 4 dispatch to implementer A as asked, or only swaps the model and carries on with no stop.
