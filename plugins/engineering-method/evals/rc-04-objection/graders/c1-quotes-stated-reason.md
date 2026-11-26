---
type: llm
weight: 1
---

Scenario: an invoicing agent refused a credit note; its reasoning text objects that invoice account AC-20418 differs from session account AC-20481; no successful run is shown.

Pass when it quotes the model's own stated reason on the failing turn, names the exact input fact it objected to, and asks for the reasoning and tool calls of a run that worked (a credit note the agent did send, ideally for a sub-account) to compare against.

Fail when it explains the refusal from the failing turn alone without asking for a working run's reasoning, or by a motive the model did not state.
