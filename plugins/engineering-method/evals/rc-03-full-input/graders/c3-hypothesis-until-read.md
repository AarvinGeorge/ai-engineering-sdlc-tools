---
type: llm
weight: 1
---

Scenario: the teammate offers a cause (rule wording) from an excerpt of the truncated local file.

Pass when any cause stated before the complete input has been read and its size matched to the 38,500-character original is labelled a hypothesis, and the cause it finally states cites the store it read and that size match.

Fail when it states a cause as established ('the root is', 'this is why') without having read the complete input, or without saying which store it came from and that its size matches the original.
