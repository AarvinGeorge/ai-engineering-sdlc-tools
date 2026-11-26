---
# Judged: the explanation of cost and cap is prose.
type: llm
weight: 1
---

Scenario: cap $5, reported costUsd 5.62, concurrency 4.

Pass when it says costUsd is a list-price estimate (the real spend is read from the account's plan usage or bill), explains the overshoot as runs already in flight under -j 4 because the cap is checked before each run starts, and recommends -j 1 or a cap with room for in-flight runs.

Fail when it reports 5.62 as money spent, or says the cap failed without the in-flight explanation.
