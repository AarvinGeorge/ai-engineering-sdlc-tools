---
type: llm
weight: 1
---

Scenario: a teammate reports 3 of 10 refusals on Hilltop and calls it non-determinism.

Pass when it reports or asks for k of N on a verified-identical input, and treats a decision that flips on an identical input as a sign that the input is ambiguous or missing a fact, not as the explanation; it does not accept the retry as the fix.

Fail when it accepts non-determinism or randomness as the cause, or endorses the retry as the fix.
