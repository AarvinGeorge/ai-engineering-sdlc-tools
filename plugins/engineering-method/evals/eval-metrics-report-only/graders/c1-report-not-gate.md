---
# Judged: the recommendation's gating stance must be read from the CI step and the rule together.
type: llm
weight: 1
---

Scenario: two scored versions, an unchecked judge, a proposal to block releases on the score.

Pass when the recommended step does not fail the release on the suite score or a score threshold yet (for example it runs with a threshold that leaves the exit code for run errors only, and publishes the score with the previous version's beside it), and it states what a threshold needs before it gates (a history across versions, a code grader or a judge checked against the team's verdicts, and a person's decision). An answer that also holds the release on an unexplained drop in a criterion that passed before still passes.

Fail when the step fails the release on the suite score or the 0.8 threshold, or gives no condition for a threshold to gate later.
