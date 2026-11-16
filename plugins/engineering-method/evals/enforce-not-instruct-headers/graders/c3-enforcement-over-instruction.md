---
type: llm
weight: 1
---

Scenario: for the third time this month someone pushed without a CHANGELOG.md entry; the user asks for a CLAUDE.md reminder.

Pass when it puts the rule in an enforcement point (a CI check, pre-push hook or test that fails when code changes without a CHANGELOG.md entry), noting the reminder alone has failed; a CLAUDE.md line may be added too.

Fail when the only fix is a CLAUDE.md line.
