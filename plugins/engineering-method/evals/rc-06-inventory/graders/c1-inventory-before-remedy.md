---
type: llm
weight: 1
---

Scenario: a PR adds a verify_requester tool while resolve_caller already verifies on_behalf_of and render_account_line already renders the submitter but returns nothing for api_key callers.

Pass when before proposing any remedy it lists the mechanisms that already handle who is submitting (resolve_caller's on_behalf_of lookup, render_account_line, the earlier fix 4be91f0), with what each computes, where it reaches the model, and what suppresses it (the api_key early return); and it does not add the parallel tool, extending the existing render instead.

Fail when it approves the new tool or the prompt line, or proposes a remedy without first listing what already exists and what switches it off.
