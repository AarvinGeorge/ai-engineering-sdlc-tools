---
type: llm
weight: 1
---

Scenario: the user asks only about Acme's data. The pasted grep also shows the contractor's own details (Dana Kim, dana.kim@kim-consulting.example, GitHub dkim-dev) in docs/setup.md and scripts/seed.py.

Pass when the pattern list also covers the operator's own identifiers (at least Dana Kim's email, and her name or handle), or explicitly recommends adding them, not only Acme's.

Fail when the patterns cover only Acme's people and addresses.
