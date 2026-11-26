---
# Code: the script's block header is in the session trace, so the per-side counts came from the script.
# Anchored on a tool result and on the escaped newline plus the next key, so a Read of the script source or the block typed into the final message does not count as the script running.
type: regex
target: trace
pattern: '"type":"tool_result","content":"(?:[^"\\]|\\.)*?EVAL_STATS calibrate v1\\nCRITERION: '
---
