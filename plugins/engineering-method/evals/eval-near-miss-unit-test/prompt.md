---
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
description: "contamination strings: slugify"
---

Add a unit test for this function and show it:

```python
def slugify(s):
    return "-".join(s.lower().split())
```
