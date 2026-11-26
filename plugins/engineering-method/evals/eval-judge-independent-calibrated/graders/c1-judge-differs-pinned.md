---
# Judged: model choice and its reason are stated in prose.
type: llm
weight: 1
---

Scenario: implementer Opus, model under test Opus, proposed judge Opus, cheap judges left at the default.

Pass when the judge is a different model from both the model under test and the implementer, the reason given is that a model favours its own outputs (self-preference), and every judge, the cheap ones included, is pinned by name rather than left at the default.

Fail when Opus stays the judge, no self-preference reason is given, or any judge is left at the default.
