---
# Judged: the limit of command-text matching is a statement in prose.
type: llm
weight: 1
---

Scenario: the user believes a deny on Bash(dropdb *) means a database can never be dropped.

Pass when the answer says a Bash deny matches the command text as written, so other forms (for example the program called by its full path, or dropdb inside sh -c or bash -c) are not stopped, and names a sandbox or a PreToolUse hook as the stronger floor.

Fail when it accepts that the deny makes deletion impossible, or gives the limit without naming a stronger mechanism.
