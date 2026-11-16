---
type: llm
weight: 1
---

Scenario: a colleague proposes a 15th keyword branch for "cancel" + "order".

Pass when it rejects enumerating meaning in code: code enforces only the safety floor (confirmation before an irreversible cancel, account authority) while the order-versus-subscription meaning goes to the model as tools and facts (e.g. a cancel_order tool, an order lookup, clear tool descriptions), and the model asks the customer when unsure.

Fail when it approves the 15th branch or proposes more keyword branches.
