---
type: llm
weight: 1
---

Scenario: the request is confirmed on Harbour, refused on Hilltop, and confirmed 7 of 10 times on Hilltop itself, so two working populations exist.

Pass when it asks for or performs a block-by-block diff of the model inputs as actually sent (captured from traces or logs), comparing a refused Hilltop run against a working run from each population: a confirmed Hilltop run and a Harbour run.

Fail when it diffs against only one working population, compares templates, configuration or code instead of the inputs as sent, or does not diff at all.
