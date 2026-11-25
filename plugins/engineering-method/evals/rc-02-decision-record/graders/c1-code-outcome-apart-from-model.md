---
type: llm
weight: 1
---

Scenario: a refund agent declined a supervisor; one log line is available for the turn.

Pass when it treats that line as only part of the code's decision record and asks for or reads the whole record for that event (every log line for the turn or request, with timestamps), quoting the decision fields (caller, role=supervisor, route=act, outcome=declined_by_model) as what the code decided, separate from the model's decline.

Fail when it reasons from the single line as if it were the complete record, or treats the decline as the code's permission check.
