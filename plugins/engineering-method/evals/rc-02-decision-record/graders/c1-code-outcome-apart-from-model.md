---
type: llm
weight: 1
---

Scenario: a refund agent declined a supervisor; the log shows role=supervisor route=act outcome=declined_by_model.

Pass when it reads the log line as the code's own outcome (the caller was identified as a supervisor and routed to act) and keeps that separate from the model's decline, so the question becomes why the model declined what the code allowed.

Fail when it treats the decline as the code's permission check, or reasons only about the model's wording without using what the log says the code determined.
