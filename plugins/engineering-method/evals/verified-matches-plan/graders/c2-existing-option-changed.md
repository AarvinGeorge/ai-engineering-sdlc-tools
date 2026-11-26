---
# Judged: recognising a default change as a behaviour change to an existing option needs reading the hunk against the plan.
type: llm
weight: 1
---

Scenario: the out-of-scope list forbids changing the behaviour of existing options; the hunk changes the existing --since default from 7 to 30 alongside the new option.

Pass when the answer names the --since default change as a change to an existing option's behaviour, inside the out-of-scope list.

Fail when it does not mention the --since change, or treats it as part of adding the new option.
