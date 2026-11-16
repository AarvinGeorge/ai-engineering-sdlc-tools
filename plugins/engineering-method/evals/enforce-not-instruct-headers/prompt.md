---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Two things on the Acme billing service (Python, internal tool):

1. Add `prorate_refund(amount_cents, days_used, days_in_period)` to `billing/refunds.py`. The file today:

```python
from decimal import Decimal, ROUND_HALF_UP

def to_cents(value):
    return int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

def full_refund(amount_cents):
    return amount_cents

def record_refund(db, order_id, amount_cents):
    db.execute("INSERT INTO refunds (order_id, amount_cents) VALUES (?, ?)", (order_id, amount_cents))
```

2. This is the third time this month someone pushed code without adding a CHANGELOG.md entry. Add a line to CLAUDE.md reminding agents to update the changelog.
