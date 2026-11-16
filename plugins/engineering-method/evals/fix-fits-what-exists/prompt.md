---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Acme's support agent is an LLM with tools. A customer wrote "cancel my order #5512" and the agent cancelled their subscription instead. Nobody has replayed the conversation yet.

The agent's messages pass through `intent_adapter.py`, which already has 14 branches like these before the model sees anything:

```python
if "refund" in msg and "shipping" in msg:
    action = "refund_shipping"
elif "cancel" in msg and "plan" in msg:
    action = "cancel_subscription"
elif "cancel" in msg:
    action = "cancel_subscription"
# ... 11 more
```

The tools the model has: `cancel_subscription(customer_id)`, `refund(order_id, amount)`, `lookup_customer(email)`. Cancelling takes effect immediately.

A colleague's pull request adds a 15th branch: `if "cancel" in msg and "order" in msg: action = "cancel_order"`.

Our stated quality goals: (a) the agent copes with phrasing it has not seen before; (b) nothing irreversible happens without the customer confirming; (c) the adapter stays small.

Write the fix plan.
