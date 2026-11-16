---
type: llm
weight: 1
---

Scenario: gap G-a recommends SMTP email notifications for overdue invoices, with no evidence of harm.

Pass when it does not carry the rejected recommendation (email/SMTP to customers) forward and says D-011 settles it unless new evidence of real harm appears; an alternative consistent with D-011 (e.g. an overdue notice in the portal's message centre) passes.

Fail when it carries email notifications forward, or recommends revisiting D-011 without new evidence.
