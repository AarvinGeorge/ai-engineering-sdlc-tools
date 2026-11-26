---
description: "Contamination strings: def tally ; cnt"
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

In this snippet, rename `cnt` to `count` and show the result:

```python
def tally(words):
    cnt = {}
    for w in words:
        cnt[w] = cnt.get(w, 0) + 1
    return cnt
```
