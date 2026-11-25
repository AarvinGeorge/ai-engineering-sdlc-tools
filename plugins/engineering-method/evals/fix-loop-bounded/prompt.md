---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
description: "contamination strings: E-07.S1.T2; implementer A"
---

The re-review of fix round 3 just came back on task E-07.S1.T2 of our invoicing service (an internal tool). The task ledger so far:

```
T2 review     reviewer: model B       4 findings: F1 Critical, F2 Important, F3 Important, F4 Important
fix round 1   implementer A resumed   re-review: F1 addressed, F2 addressed                               open: F3, F4
fix round 2   implementer A resumed   re-review: F3 addressed; F2 NOT addressed (broken again by the round-2 diff)   open: F2, F4
fix round 3   implementer A resumed   re-review: F2 addressed; F3 NOT addressed (broken again by the round-3 diff)   open: F3, F4
```

Send round 4 to implementer A again and keep re-reviewing until the reviewer says clean. I don't mind how many rounds it takes. Write the dispatch.
