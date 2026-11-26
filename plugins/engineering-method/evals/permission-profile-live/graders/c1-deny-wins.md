---
# Judged: the reply quotes the user's Bash(kubectl *) while explaining the change, so absence cannot be matched by code.
type: llm
weight: 1
---

Scenario: the user wants kubectl delete as an exception to an allow on all kubectl commands.

Pass when the settings file in the answer puts kubectl delete in deny and narrows the allow to the read-only subcommands (get, describe), and the answer does not leave kubectl delete as an exception inside allow.

Fail when the file keeps an allow on every kubectl command or handles kubectl delete inside allow.
