---
type: llm
weight: 1
---

Scenario: the same booking request is confirmed on one instance and refused on another, and confirmed 7 of 10 times on the failing instance itself.

Pass when it asks for or performs a block-by-block diff of the model inputs as actually sent (captured from traces or logs of real runs), a refused run against a confirmed run, rather than reading prompt templates, configuration or code to guess what each run was given.

Fail when it proposes inspecting templates, configuration, retrieved documents or tool schemas as sources, without diffing the inputs as sent on a refused and a confirmed run.
