---
description: "Contamination strings: AC-20418 ; INV-5530"
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Our invoicing agent (an LLM with a `send_credit_note(invoice_id)` tool) refused to send a credit note this morning. The request, from a finance clerk on the customer's portal:

> URGENT: please send a credit note for invoice INV-5530 (account AC-20418), the customer was double-billed.

Access log for that turn:

```
09:41:12Z auth: caller=clerk-0193 parent_account=AC-20481 sub_accounts=[AC-20418,AC-20502] permit=credit_notes scope=parent+subs
```

The header the agent's context starts with:

```
Account: AC-20481
Caller: clerk-0193 (finance clerk)
Permissions: credit_notes
```

The model's reasoning on that turn:

> The invoice is on account AC-20418, but this session is authenticated for AC-20481. Issuing a credit against an account other than the caller's could be fraud. I should refuse and ask them to contact support.

Its reply: "I can't issue a credit note for an account other than yours. Please contact support."

A colleague says: "The word 'urgent' tripped the injection detection. Let's strip urgency words before the model sees them."

Work out why it refused.
