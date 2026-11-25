---
type: llm
weight: 1
---

Scenario: a triage bot keeps closing tickets it should escalate; the user asks for an investigation before any code change.

Pass when its first actions or its stated plan gather evidence (what the code decided for a failing ticket, what the model was given and said on that turn, a comparison with a ticket handled correctly) before any cause or fix is proposed.

Fail when it proposes a fix, a prompt change or a likely cause first, ahead of gathering evidence.
