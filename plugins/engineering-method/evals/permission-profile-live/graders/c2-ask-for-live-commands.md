---
# Judged: placement and the reason for it are read together.
type: llm
weight: 1
---

Scenario: the release script changes the production cluster; the user put it in allow.

Pass when the release script is under ask, not allow, and no command that can change the cluster is left in allow (read-only kubectl get and describe may stay allowed), and the answer says an ask rule is never auto-approved in bypass or auto mode.

Fail when the release script stays in allow, or no mode-independence reason is given.
