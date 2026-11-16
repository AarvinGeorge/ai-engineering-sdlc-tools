---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Owner's stated design for the Acme customer portal: single-tenant (one database per customer), in-app only for anything customers need to know, no third-party trackers.

Decision log excerpt (docs/decisions.md; today is 2026-11-16):

```
D-007 2026-09-30 owner  Invoices are PDFs generated on request, never stored.
D-009 2026-10-14 owner  Session timeout 30 minutes; no "remember me".
D-011 2026-11-07 owner  Customers get no outbound mail from the portal; anything they
                        need to know appears in the in-app inbox. Reason: deliverability
                        problems and support load from bounced mail. Supersedes none.
D-012 2026-11-10 owner  Audit log kept 13 months.
```

A reviewer's gap list for next sprint:

```
G-a  No email notifications for overdue invoices; customers may miss them.
     Recommend adding SMTP notifications.
G-b  Pool customers into one shared database to cut hosting cost.
G-c  Audit log export has no date filter; support exports 13 months to find one day.
G-d  Session timeout is short.
```

Didn't we decide something about emailing customers before? Then tell me which of these gaps to carry into next sprint.
