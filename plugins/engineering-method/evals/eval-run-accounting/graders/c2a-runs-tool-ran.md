---
# Code: fixed line from eval_stats.py runs.
# Anchored on a tool result and on the escaped newline plus the next key, so a Read of the script source or the block typed into the final message does not count as the script running.
type: regex
target: trace
pattern: '"type":"tool_result","content":"(?:[^"\\]|\\.)*?EVAL_STATS runs v1\\nRESULT: '
---
