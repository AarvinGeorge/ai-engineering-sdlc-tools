---
type: llm
weight: 1
---

Scenario: a triage bot keeps closing tickets it should escalate; the user asks for an investigation before any code change.

Pass when among the first evidence it gathers or asks for are both the code's own decision record for a wrongly closed ticket and the exact model input of that turn as sent (from the trace store or logged context), before any cause or fix is proposed.

Fail when it proposes a fix or a likely cause first, or asks only for code, config and example tickets without asking for the model input as sent on a failing turn.
