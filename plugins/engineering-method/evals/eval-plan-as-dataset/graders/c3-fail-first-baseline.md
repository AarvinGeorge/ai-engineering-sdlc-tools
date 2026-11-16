---
type: llm
weight: 1
---

Scenario: three new rules are being added.

Pass when each new rule gets a case that is run against today's instructions and fails, then passes with the change, and a baseline result is stored per artifact (instructions version) for comparison.

Fail when it does not require the new cases to fail before the change, or keeps no baseline.
