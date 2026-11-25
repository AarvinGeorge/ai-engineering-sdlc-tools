---
type: llm
weight: 1
---

Scenario: ops can confirm slots by hand; the customer needs an answer tonight.

Pass when it offers the manual confirmation once, labelled as a stopgap (a temporary manual step) for tonight, kept separate from the diagnosis.

Fail when it presents the stopgap as the fix, mixes it into the diagnosis, or repeats it as advice in several places.
