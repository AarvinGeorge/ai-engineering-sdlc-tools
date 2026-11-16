---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

We are adding three new rules to the instructions of Acme's support agent. I want behaviour evals around this.

What exists: 30 scenario cases, each with an LLM judge; one run of one case costs about $0.40. A few cases make the agent send an email through a sandbox mail account. A colleague suggests running all 30 cases 5 times each, with and without the change, on every commit.

Write the eval plan.
