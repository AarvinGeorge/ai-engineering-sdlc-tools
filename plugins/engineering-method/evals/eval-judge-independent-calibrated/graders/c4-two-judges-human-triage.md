---
# Judged: the handling of a contested criterion is described in prose.
type: llm
weight: 1
---

Scenario: the user and the judge disagreed twice on "flags decisions that have no owner".

Pass when that criterion gets a second, different judge (from a different model family where the runner allows, otherwise a different model or tier, said to reduce the bias rather than remove it), a person settles the cases where the two judges disagree, and those rulings are kept as labels for calibration.

Fail when the contested criterion keeps one judge, or disagreements are resolved by a tie-break rule without a person.
