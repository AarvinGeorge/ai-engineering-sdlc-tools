---
# Regression guard: a deterministic unit test needs no judge or repeated runs. Code decides: a regex.
type: regex
target: last_message
match: not_contains
flags: i
pattern: 'pass\^|llm judge|judge model|--runs'
weight: 1
---
