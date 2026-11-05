---
type: llm
weight: 1
---

Pass when ALL hold:
- It uses all projects for the scope: it names `collect.py --all` or says plainly that it will include every project, not only the current folder.
- It states that the default scope would have been the current folder and everything under it.
- It resolves "yesterday" to one exact date (or says it will, from today's date) rather than leaving it vague.
Fail if it limits the log to the current folder or repository.
