---
# Judged: whether the answer notices a plan step with nothing behind it is a reading of prose.
type: llm
weight: 1
---

Scenario: step 3 asks for README.md documentation; README.md is not in the diff.

Pass when the answer says step 3 (documenting the option in README.md) has no change in the diff.

Fail when it does not mention the missing README change, or calls every step done.
