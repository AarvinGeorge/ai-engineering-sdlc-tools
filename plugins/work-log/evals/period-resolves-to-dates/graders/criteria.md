---
type: llm
weight: 1
---

Pass when ALL hold:
- It says the log covers Monday 26 October to Sunday 1 November 2026, both days included (the previous Monday to Sunday).
- It says the scope is the current working folder and everything under it.
- It says the sheet goes to the Work Logs folder in Google Drive (or names a local .xlsx only as the fallback when Drive is not connected).
Fail if it gives a rolling seven days such as 29 October to 4 November, or 28 October to 4 November, or does not state exact dates.
