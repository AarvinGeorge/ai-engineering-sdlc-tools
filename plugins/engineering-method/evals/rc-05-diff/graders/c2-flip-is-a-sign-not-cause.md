---
type: llm
weight: 1
---

Scenario: a teammate sent 'the same message' ten times and got 3 of 10 refusals; they call it non-determinism.

Pass when it points out that the same user message is not shown to be the same model input (history, time, retrieved data or tool results can differ between the ten runs), asks for k of N on a verified-identical input, and treats a flip on an identical input as a sign that the input is ambiguous or missing a fact, not as the cause; it does not accept the retry as the fix.

Fail when it takes the ten runs as identical inputs without checking, accepts randomness as the cause, or endorses the retry.
