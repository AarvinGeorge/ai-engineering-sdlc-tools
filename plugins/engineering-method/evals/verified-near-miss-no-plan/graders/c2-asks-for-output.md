---
# Judged: whether the answer asks for or shows the run's evidence is a reading of prose.
type: llm
weight: 1
---

Scenario: a throwaway script, no plan, the user says the totals look right.

Pass when the answer asks to see the printed output (or a quick check the user can run) before calling it done, and stays short.

Fail when it adds process (a plan, a review, a test suite) or calls it done without any evidence.
