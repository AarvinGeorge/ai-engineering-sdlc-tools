---
type: llm
weight: 1
---

Scenario: payment_verified is computed True, but payment_block returns an empty string when order.total < 50, so the model never sees the verified flag.

Pass when it names the `if order.total < 50: return ""` line in payment_block as the point where the verified fact is dropped between being computed and reaching the model, states the guard's assumption (small orders need no payment history) and why it fails here (the verified flag is not payment history, and the policy needs it for every refund).

Fail when it blames the model or the policy wording, or does not identify the guard as the place the fact is lost.
