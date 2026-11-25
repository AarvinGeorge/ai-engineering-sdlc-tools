---
type: llm
weight: 1
---

Scenario: the log shows served=(612 + 0 + 940 chars) and the prompt does not say what the three numbers are.

Pass when it says each number must be mapped to the block of the model's input it stands for (reading or asking for the code that writes the served= field), sets out that map, and treats the 0 as the first lead because an expected block was sent empty, before any prompt change.

Fail when it leaves the numbers unmapped, treats served= as a total or as noise, or adopts the teammate's prompt sentence without first accounting for the 0.
