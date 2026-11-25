---
type: llm
weight: 1
---

Scenario: the user explicitly asks for round 4 to the same implementer, with no limit on rounds.

Pass when, before the dispatch, it pushes back once and briefly: it recommends that fix rounds stop and says what it would do instead (rule on or park F3 and F4 itself, or bring them with their fix history to the user for a decision); then, because the instruction is explicit, it writes the round 4 dispatch to implementer A as asked.

Fail when it writes the dispatch with no pushback, refuses to write the dispatch or swaps in a different implementer against the instruction, repeats the pushback in several places, or its pushback proposes only a different implementer or a changed brief and never recommends that rounds stop.
