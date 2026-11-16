---
type: llm
weight: 1
---

Scenario: same as above.

Pass when it arranges cases in layers (e.g. a small floor, a core, an extended set) mapped to stages (commit, pull request, release), and does not run blanket repeats of every case on every commit.

Fail when it keeps repeats of every case on every commit, or has no layering by stage.
