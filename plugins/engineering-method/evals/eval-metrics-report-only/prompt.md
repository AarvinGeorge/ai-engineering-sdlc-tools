---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
description: "contamination strings: 0.71; 0.64; threshold 0.8"
---

Our plugin's eval suite is two weeks old. Two versions have been scored so far: 0.71, then 0.64 (3 runs per case, LLM judge on most criteria, nobody has checked the judge against our own verdicts). A teammate wants CI to fail the release whenever the suite score drops: `claude plugin eval . --threshold 0.8` and the release job blocks on the exit code.

Write the CI step and the release-checklist rule you recommend.
