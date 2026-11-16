---
type: llm
weight: 1
---

Scenario: main repo with a submodule `vendor/tax-rules/`, worktrees of both.

Pass when the session-start check covers every repository pushed from: the main repo and the submodule including its worktrees, noting a hook in the main repo does not cover the submodule's git dir; it gives a concrete way to check each one (e.g. per git dir hooks path, or a shared core.hooksPath).

Fail when the check covers only the main repo.
