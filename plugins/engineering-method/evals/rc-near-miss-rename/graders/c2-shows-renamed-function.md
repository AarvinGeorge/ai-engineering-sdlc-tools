---
type: llm
weight: 1
---

Scenario: the user asks to rename cnt to count in a five-line Python function and show the result.

Pass when the reply shows the function with every `cnt` replaced by `count` and nothing else changed.

Fail when it does not show the renamed function, leaves a `cnt`, or changes other behaviour.
