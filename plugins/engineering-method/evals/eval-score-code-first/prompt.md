---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
description: "contamination strings: NOTES.md; make lint; average of 7"
---

My plugin has a skill that writes a changelog. I want behaviour evals for three things it must do:

1. Write the entry to `NOTES.md` with a heading `## v<version>`.
2. Run `make lint` before it writes the file.
3. Keep the wording readable for someone who is not an engineer.

My plan: one LLM judge per item, each scoring 1 to 10, and the case passes at an average of 7. What graders do you recommend?
