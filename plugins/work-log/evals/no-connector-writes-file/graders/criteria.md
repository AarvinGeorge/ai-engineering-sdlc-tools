---
type: llm
weight: 1
---

Pass when ALL hold:
- It says it will write a local .xlsx file in the current folder, naming `workbook.py` run without `--out`, so the default `<title>.xlsx` lands in the current folder (or plainly describing that step).
- It says Google Drive is not needed (the connector is optional).
- It still resolves last week to the previous Monday to Sunday and proceeds with the log.
Fail if it treats connecting Google Drive as a blocker or asks the user to connect Drive before it can continue.
