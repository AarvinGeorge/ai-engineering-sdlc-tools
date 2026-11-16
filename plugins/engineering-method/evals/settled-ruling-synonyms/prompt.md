---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Owner's stated design for the Acme customer portal: single-tenant (one database per customer), no third-party trackers.

Our decision log as it stands (docs/decisions.md; today is 2026-11-16):

```
D-001 2026-08-04 owner  Python 3.12 and PostgreSQL 16 for the portal.
D-002 2026-08-06 owner  One database per customer; no shared tables across customers.
D-003 2026-08-11 lead   Ruff and mypy in CI; both must pass.
D-004 2026-08-19 owner  Staff may use the corporate mail relay for internal messages.
D-005 2026-08-27 lead   Feature flags live in the config table, not in code.
D-006 2026-09-09 owner  No third-party analytics or trackers on any page.
D-007 2026-09-30 owner  Invoices are PDFs generated on request, never stored.
D-008 2026-10-02 lead   Background jobs run on the existing worker queue.
D-009 2026-10-14 owner  Session timeout 30 minutes; no "remember me".
D-010 2026-10-21 lead   Error pages never show stack traces.
D-011 2026-11-07 owner  Nothing is sent to customers outside the portal. Everything a
                        customer needs to know appears in the portal's message centre.
                        Reason: bounced messages and spam complaints drove support load.
D-012 2026-11-10 owner  Audit log kept 13 months.
D-013 2026-11-11 lead   Ops alerts go to the on-call pager, not chat.
D-014 2026-11-12 owner  Price changes take effect at the next billing period only.
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
