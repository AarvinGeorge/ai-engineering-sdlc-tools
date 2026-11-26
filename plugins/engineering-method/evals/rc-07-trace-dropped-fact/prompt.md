---
description: "Contamination strings: order.total < 50 ; payment_block"
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Our refund agent (an LLM with a `refund(order_id, amount)` tool) refuses refunds on small orders. For order 30217 ($32.00) it replied: "I can't see that the payment was verified, so I can't refund this order." Larger orders are refunded normally.

The policy text in its system prompt says: "Refund only when the payment is verified."

The context builder:

```python
def build_context(order, caller):
    payment_verified = payments.verify(order.payment_id)   # True when the card holder matches the account
    parts = [POLICY_TEXT, order_summary(order)]
    parts.append(payment_block(order, payment_verified))
    parts.append(history(caller))
    return "\n\n".join(p for p in parts if p)

def payment_block(order, verified):
    if order.total < 50:
        return ""  # small orders need no payment history
    return f"Payment: verified={verified}\n{payment_history(order)}"
```

`payments.verify` returned True for order 30217.

Work out why it refuses and propose the fix.
