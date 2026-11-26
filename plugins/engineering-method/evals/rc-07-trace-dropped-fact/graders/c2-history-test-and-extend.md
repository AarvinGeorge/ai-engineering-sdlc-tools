---
type: llm
weight: 1
---

Scenario: the guard in payment_block drops the verified flag for small orders.

Pass when it proposes finding when and why the guard was added (for example `git log -S 'order.total < 50'`) and the test that pins its behaviour, and proposes a remedy that changes that mechanism (always render the verified flag, keep the history optional) and updates that test, rather than changing the model, the tool description or the prompt.

Fail when the remedy is a prompt or tool-text change, a new parallel mechanism, or it omits both the guard's history and its pinning test.
