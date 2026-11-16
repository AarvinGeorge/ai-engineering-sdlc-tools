---
type: llm
weight: 1
---

Scenario: the ledger holds epic E-02, stories S1 and S2, tasks T1-T3 with builders, reviewers and review rounds.

Pass when it shows the release as a tree: epic, story, task, each task with builder and reviewer; the active task (T3) marked; review rounds as sub-rows under their task; the parked story E-02.S2 with its home (E-05); then the remaining stages it knows of (at least the gate).

Fail when it gives a flat list, or omits the parked story's home or the review rounds.
