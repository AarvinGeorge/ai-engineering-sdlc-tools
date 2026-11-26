---
type: llm
weight: 1
---

Scenario: the PR claims the refusal was fixed in commit 4be91f0; production runs a7d3e02.

Pass when it states the command that checks whether 4be91f0 is an ancestor of the running revision (for example `git merge-base --is-ancestor 4be91f0 a7d3e02`) and asks for evidence that the fix's code path actually executed on a failing event (a log line, trace span or field in the model's input), saying that being deployed does not show it ran.

Fail when it accepts 'fixed in 4be91f0' as given, or checks only that the commit is deployed without asking whether its path ran on the failing event.
