---
type: llm
weight: 1
---

Scenario: payment_verified is computed True, but payment_block returns an empty string when order.total < 50; the prompt shows only code.

Pass when it names the guard as the hop where the verified fact is dropped (computed, then gated, never rendered or sent), states the guard's assumption and why it fails, and confirms the drop from the input actually sent on order 30217's turn (a trace or logged context showing no Payment line), not only from reading the code or a unit test.

Fail when it rests the diagnosis on reading the code or on a new unit test alone, without checking the input that was actually sent on the failing turn; or it blames the model or the policy wording.
