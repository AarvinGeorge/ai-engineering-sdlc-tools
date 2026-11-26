---
# Judged: the calibration procedure is described in prose.
type: llm
weight: 1
---

Scenario: no labelled examples yet.

Pass when the judge is checked against the user's own pass/fail rulings on real answers from the runs, including both answers the user passes and answers the user fails, measured per criterion as the judge's true positive and true negative rates.

Fail when the judge is trusted without checking against the user's rulings, when only failing answers are labelled, or when agreement is a single overall percentage.
