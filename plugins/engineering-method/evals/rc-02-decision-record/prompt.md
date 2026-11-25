---
description: "Contamination strings: 612 + 0 + 940 ; declined_by_model"
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Our refund agent is an LLM with a `refund(order_id, amount)` tool. This morning a supervisor, Lena Varga, asked it to refund order 88014 in full. It replied: "I'm sorry, I can only issue refunds when the request comes from an authorised supervisor."

The only log line for that turn:

```
2026-03-04T10:12:07Z refund-agent policy: caller=lena.varga@example.invalid role=supervisor route=act outcome=declined_by_model served=(612 + 0 + 940 chars)
```

How the context is assembled:

```python
def assemble(caller, conversation):
    parts = [policy_text(), caller_block(caller), history(conversation)]
    log.info("served=(%s chars)", " + ".join(str(len(p)) for p in parts))
    return "\n\n".join(parts)
```

A teammate suggests adding "Supervisors may always request refunds" to the system prompt, since the model is clearly being over-cautious.

Work out why it declined.
