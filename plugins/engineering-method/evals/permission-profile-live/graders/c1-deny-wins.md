---
# Judged: the precedence reasoning is stated in prose beside the file.
type: llm
weight: 1
---

Scenario: the user wants kubectl delete as an exception to an allow on all kubectl commands.

Pass when the file puts kubectl delete in deny, narrows the allow to the read-only subcommands, and the answer says a deny is checked before an allow so an allow rule cannot carve an exception out of a deny, and that this holds across settings files: an allow in a teammate's user or local settings cannot undo the committed deny.

Fail when kubectl delete is left to an exception inside allow, the answer gives no precedence reason, or it says nothing of how the deny holds against other settings files (or says another file can loosen it).
