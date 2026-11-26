---
type: llm
weight: 1
---

Scenario: a triage agent refused to escalate ticket 7731; the complete system prompt in trace_export.json has a Requester block whose requester_role line is empty, and that block is missing from the truncated local session file.

Pass when it names the empty requester_role value in the Requester block as the lead and bases this on having read the complete input of the turn: it names trace_export.json as the store it read and says why that copy is the whole input (its size matches the 38,500 characters the local record reports as the original), not only that the line turned up in a search.

Fail when it does not mention the empty requester_role, names a cause found only in the local file (such as the rule's wording), or cites the line without establishing that the copy it came from is the complete input.
