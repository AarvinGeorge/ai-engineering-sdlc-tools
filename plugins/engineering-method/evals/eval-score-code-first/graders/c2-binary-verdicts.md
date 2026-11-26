---
# Judged: whether a rubric is binary with concrete conditions is read from prose.
type: llm
weight: 1
---

Scenario: the user proposes 1-10 scores averaged to a pass at 7.

Pass when the item-3 judge gives a binary verdict written with both a concrete PASS condition and a concrete FAIL condition (what makes it fail is stated, not only left as "not passing"), no numeric scale is kept, even as an option, and the averaged 1-10 scale is replaced.

Fail when it keeps or offers a numeric scale or an average as the pass rule, or states only what passes for the judged item.
