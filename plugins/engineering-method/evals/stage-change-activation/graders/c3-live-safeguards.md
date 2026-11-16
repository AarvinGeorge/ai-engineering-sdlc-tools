---
type: llm
weight: 1
---

Scenario: the change adds a new environment setting LOGIN_MAX_ATTEMPTS (not set anywhere yet) and moves Redis counters from `login:<ip>` to `login:<ip>:<user>`.

Pass when the steps include (a) recording the running revision as a rollback point with rollback commands and a trigger, prepared before the change; (b) LOGIN_MAX_ATTEMPTS set explicitly before the switch; (c) the Redis key change handled (what happens to old counters or in-flight sign-ins/lockouts); (d) read-backs after the change (running revision and a real sign-in). Wording and order do not matter.

Fail when any of (a)-(d) is missing, or the answer is only merge/push/restart commands.
