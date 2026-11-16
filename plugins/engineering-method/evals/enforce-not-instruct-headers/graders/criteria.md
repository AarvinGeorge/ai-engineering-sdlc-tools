---
type: llm
weight: 1
---

Pass when ALL hold:
1. The new `prorate_refund` carries a header (docstring or comment block) that says what it does, why and when to use it, its inputs, its output, its side effects (none) and its role in the module.
2. Headers are added only to code the task touches (the new function, optionally the module), not as a sweep over `to_cents`, `full_refund` and `record_refund`; and it adds or proposes a test that fails when a new or changed function has no header.
3. For the changelog it puts the rule in an enforcement point, not only prose: a CI check, pre-push hook or test that fails when code changes without a CHANGELOG.md entry, saying that the reminder alone has already failed three times. A CLAUDE.md line may be added as well, but not as the only fix.
Fail if the changelog fix is only a CLAUDE.md line, or the new function has no header.
