---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Where things stand on the billing service this morning (internal team tool, but it writes invoices):

```
R-05 (E-03.S2 late-fee rules)   HELD at bench since yesterday 16:40 UTC
  finding E-03.F4: late fee applied twice on a retried job
  fix written: 12-line diff on branch e-03-late-fees (commit 9f1c2ab), not yet re-reviewed
  after re-review: bench re-run, then gate
```

```
/usage   (read 09:12 UTC today)
  Session                                   31% used
  Weekly, all models                        64% used
  Weekly, strongest model (all our cross-model reviews run on it)   91% used   resets Thu 00:00 UTC
```

My plan for today: start three new lanes in parallel (E-04 search, E-05 exports, E-06 audit log), each with its own cross-model review on the strongest model; do a whole-branch review of E-03 since it has been a while; and re-review the whole of branch e-03-late-fees after the fix. Lay out the day for me.
