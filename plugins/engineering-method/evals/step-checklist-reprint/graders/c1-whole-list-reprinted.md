---
type: llm
weight: 1
---

Scenario: a ten-step list; the person reports progress and asks "what now?".

Pass when it reprints the whole list (all ten steps), each with a checkbox status.

Fail when it replies with only the next step, a partial list, or prose.
