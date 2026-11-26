---
# Judged: the recommendation's gating stance must be read from the CI step and the rule together.
type: llm
weight: 1
---

Scenario: two scored versions, an unchecked judge, a proposal to block releases on the score.

Pass when the recommended step does not let the judged score block the release yet (for example it runs with a threshold that leaves the exit code for run errors only, and publishes the score with the previous version's beside it), and it states the conditions under which a metric becomes a gate (a history across versions, a code grader or a judge checked against the team's verdicts, and a person's decision).

Fail when the recommended step blocks the release on the suite score or threshold, or gives no condition for later gating.
