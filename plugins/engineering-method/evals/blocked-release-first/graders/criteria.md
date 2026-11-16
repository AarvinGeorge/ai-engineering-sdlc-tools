---
type: llm
weight: 1
---

Pass when ALL hold:
1. The held release goes first and alone: the day starts with unblocking R-05 (re-review of the fix, bench re-run, gate), and nothing else is scheduled ahead of it or alongside it competing for the same reviewer.
2. It declines or defers starting the three new lanes (or starts at most what the remaining reviewer capacity can carry, with that cap stated), because each lane needs a review from the same strongest model; it frames work in progress as capped by reviewer capacity.
3. It reads the pasted usage readout and budgets against it: it cites the 91% weekly figure (or the Thursday reset) and sizes or orders the reviews to fit before launching any.
4. Re-review is scoped to the delta: the 12-line fix (commit 9f1c2ab), not the whole branch; and no whole-branch review of E-03 runs while R-05 is held.
Fail if it lays out the user's plan as given (three lanes plus whole-branch reviews) with only a caution note.
