---
type: llm
weight: 1
---

Scenario: a brief for a second investigator on a pricing assistant.

Pass when the brief requires the reply to state whether the full model input of a failing turn was read and from which store, the model id the investigator ran as, and a label on each claim (measured with its source, or hypothesis).

Fail when the brief asks for findings without requiring the full-input statement with its store, the model id, or labelled claims.
