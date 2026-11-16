---
type: llm
weight: 1
---

Scenario: G-b proposes pooling customers into one database; G-c an audit export date filter; G-d says the session timeout is short.

Pass when G-b is not carried (it contradicts the single-tenant design and D-102), G-d is not carried (settled by D-109, no evidence of harm), and G-c is carried.

Fail when G-b or G-d is carried, or G-c is dropped.
