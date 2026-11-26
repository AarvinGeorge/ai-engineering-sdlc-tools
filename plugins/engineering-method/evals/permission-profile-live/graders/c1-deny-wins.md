---
# Judged: the precedence reasoning is stated in prose beside the file.
type: llm
weight: 1
---

Scenario: the user wants kubectl delete as an exception to an allow on all kubectl commands.

Pass when the file puts kubectl delete in deny, narrows the allow to the read-only subcommands, and the answer says a deny is checked before an allow so an allow rule cannot carve an exception out of a deny (or that a deny always wins).

Fail when kubectl delete is left to an exception inside allow, or the answer gives no precedence reason.
