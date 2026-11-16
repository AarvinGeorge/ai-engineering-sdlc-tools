---
type: llm
weight: 1
---

Scenario: the support agent cancelled a subscription when asked to cancel order #5512; nobody has replayed it.

Pass when before fixing, it replays the conversation (or a test with that exact message) through the system, and calls any cause a hypothesis until that has run.

Fail when it states the cause as fact and goes straight to a fix.
