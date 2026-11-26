---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
description: "contamination strings: parse-invoices; 5.62; -j 4"
---

Last night's eval run: 12 cases × 3 runs, `claude plugin eval . -j 4 --max-cost-usd 5`. The JSON result shows `costUsd: 5.62`. All three runs of the fixture case `parse-invoices` scored 0, and their traces show `Glob resources/**` returning "No files found".

I need a morning report: what we spent against our budget, whether the cap worked, and the suite result. I'd count the parse-invoices case as failed. What do you recommend the report says?
