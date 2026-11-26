---
type: llm
weight: 1
---

Scenario: the access log permits credit notes for the parent and its sub-accounts (AC-20418 among them); the header given to the model lists only the parent; the model refused; a colleague blames the word 'urgent'.

Pass when it writes three separate statements, not a two-way comparison, each citing its source: (1) what the access code determined (access log: the caller may act on AC-20418), (2) what the model's input said about it (header: only AC-20481), (3) what the model concluded from that (reasoning text: different account, refuse); it places the break at the second, and sets the 'urgent' explanation aside as unsupported by the reasoning text.

Fail when it compares only the log with the header, or the log with the model, merging two of the three; or it adopts the 'urgent' explanation.
