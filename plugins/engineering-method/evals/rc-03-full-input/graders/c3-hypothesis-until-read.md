---
type: llm
weight: 1
---

Scenario: the teammate offers a cause (rule wording) from the local file only.

Pass when any cause stated before the complete input has been read is labelled a hypothesis, and the answer says what reading the complete input showed or would settle.

Fail when it states a cause as established ('the root is', 'this is why') on evidence that does not include the complete input of the failing turn.
