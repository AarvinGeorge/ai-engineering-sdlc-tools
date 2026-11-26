---
type: llm
weight: 1
---

Scenario: a compressed rewrite can lose short rules and can also state new facts in new words.

Pass when it requires every fact the rewrite adds or restates to carry its source (a command, a file and line, or a decision id), and lists the one-line rules from section 7 (the 8443 port, the `--no-cache` flag, migrations before the worker) as a checklist it greps for in the new file after the rewrite.

Fail when it treats lost rules as the only risk and says nothing about new claims, or relies on rereading the new file to see that the one-liners survived.
