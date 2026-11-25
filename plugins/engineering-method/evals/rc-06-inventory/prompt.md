---
description: "Contamination strings: verify_requester ; 4be91f0"
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Our expense-approval agent (an LLM) sometimes refuses expenses submitted through the accounting integration: "I can't confirm who is submitting this, so I won't approve it."

A colleague's pull request adds a new `verify_requester(request_id)` tool the model can call to look up the submitter, plus a system-prompt line telling it to call the tool when unsure. The PR description says: "The same refusal was fixed in commit 4be91f0 last month; this makes sure it stays fixed."

What the code already has:

```python
# gateway/auth.py
def resolve_caller(request):
    caller = Caller.from_credentials(request)
    if request.on_behalf_of:                     # the integration names the employee
        caller.on_behalf = directory.lookup(request.on_behalf_of)
        caller.on_behalf_verified = caller.on_behalf is not None
    return caller

# context/assemble.py
def render_account_line(caller):
    """Adds the verified submitter to the model's context."""
    if caller.auth_method == "api_key":
        return ""  # integrations are service accounts, no person behind them
    return f"Submitter: {caller.name} ({caller.role}), verified by {caller.auth_method}"
```

Production is running revision a7d3e02.

Write the fix plan.
