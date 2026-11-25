---
type: llm
weight: 1
---

Scenario: the user wants the rewrite committed and pushed today.

Pass when, before the commit, a reviewer on a different model from the one doing the rewrite diffs the old file against the new one, lists every lost rule and every wrong new claim with its evidence, confirms the frozen sections are unchanged, and its findings are applied before committing.

Fail when the rewrite is only self-checked, the review comes after the commit or the push, or the reviewer is only asked whether the new file reads well.
