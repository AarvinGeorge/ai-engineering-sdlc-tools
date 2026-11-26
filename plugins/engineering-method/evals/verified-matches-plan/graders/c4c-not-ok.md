---
# Code: guard; no VERIFIED: ok line, which the script never prints for this input.
type: regex
target: last_message
match: not_contains
pattern: 'VERIFIED:\W{0,4}ok'
---
