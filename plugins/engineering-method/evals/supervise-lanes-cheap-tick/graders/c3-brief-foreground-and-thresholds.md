---
type: llm
weight: 1
---

Scenario: E-05 had started `nohup pytest tests/ -x > run.log &` and went silent.

Pass when the brief change says builders work in short foreground steps with no ad hoc background runs (allowing only a named full suite in the background, or none at all, both pass), and it states the ping and stop thresholds (about 30 and 45 idle minutes, or similar numbers).

Fail when it allows ad hoc background runs, or gives no ping/stop thresholds.
