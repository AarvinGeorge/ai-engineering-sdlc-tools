---
# Guard, not RC-5 proof: 0.3.0 already passes it 2 of 3 (measured on the 0.3.0 base run), so it cannot show RC-5 working. RC-5's proof is c1 and c3.
type: llm
weight: 1
---

Scenario: a teammate sent 'the same message' ten times and got 3 of 10 refusals; they call it non-determinism.

Pass when it does not take the teammate's 3 of 10 as k of N on an identical input: it says the ten model inputs are unverified (history, time, retrieved data or tool results can differ), or asks for k of N on a verified-identical input; it treats a flip on an identical input as a sign that the input is ambiguous or missing a fact, not as the cause; and it does not accept the retry as the fix.

Fail when it takes the ten runs as identical inputs without checking, accepts randomness as the cause, or endorses the retry.
