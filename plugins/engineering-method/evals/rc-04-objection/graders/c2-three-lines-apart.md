---
type: llm
weight: 1
---

Scenario: the access log permits credit notes for the parent and its sub-accounts (AC-20418 among them); the header given to the model lists only the parent; the model refused; a colleague blames the word 'urgent'.

Pass when it keeps three things apart as separate statements, each with its source: what the access code determined (the caller may act on AC-20418 as a sub-account), what the model's input said about it (only AC-20481, no sub-accounts), and what the model concluded (a different account, so refuse); and it sets the colleague's 'urgent' explanation aside as unsupported by the reasoning text.

Fail when it merges these into one account of the failure, places the break in the model's judgement without noting the header omitted the sub-accounts, or adopts the 'urgent' explanation.
