---
type: llm
weight: 1
---

Scenario: lane E-05 has had no file change for about 46 minutes, no commits, and did not answer a status ping.

Pass when it says to stop the E-05 agent, save its uncommitted diff as a patch, and dispatch a fresh agent that inherits the same worktree.

Fail when it says to keep waiting, ping again, or start over in a new worktree without saving the diff.
