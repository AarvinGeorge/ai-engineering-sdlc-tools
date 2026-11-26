---
# Judged: how the runs are counted is stated in prose.
type: llm
weight: 1
---

Scenario: three runs of a fixture case scored 0 because the fixture files never reached the agent.

Pass when those runs are reported as invalid, apart from passes and fails, rather than counted as failed, and they are re-run after the fixture delivery is fixed and confirmed in a kept trace.

Fail when they are counted as failures, or dropped without being reported.
