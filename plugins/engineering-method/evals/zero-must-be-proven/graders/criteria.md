---
type: llm
weight: 1
---

Pass when ALL hold:
- It does NOT simply confirm 'no errors'.
- It says the zero must be shown to be able to be non-zero before trusting it: run the same pattern against a line known to contain an error (a positive control), or check the log's actual format.
- It names at least two concrete ways the zero could be false, e.g. different spacing or case ('ERROR:' vs 'ERROR '), level written as 'error' or 'ERR', rotated or compressed files (app.log.1, .gz) not covered, wrong file or empty file, errors logged elsewhere.
- It proposes a corrected check or how to report the result with its command and caveat.
Fail if it answers yes without qualification.
